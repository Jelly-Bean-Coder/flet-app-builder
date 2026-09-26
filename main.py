# -----------------------------------------------------------------------------
# Copyright (c) 2026 Jordan Al-Fanek. All rights reserved.
# Licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0
# International (CC BY-NC-SA 4.0).
#
# This software is provided "AS-IS" without any warranties.
# -----------------------------------------------------------------------------

import json
from datetime import datetime, timedelta

import flet as ft

exams = []
prefs = None


async def main(page: ft.Page):
    global prefs

    # Initialize Flet 1.0 SharedPreferences service
    prefs = ft.SharedPreferences()
    page.title = "Exam Study Planner"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # Persistent layout container to display rows of added exams dynamically
    exams_container = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5)

    # Input elements
    name_text = ft.TextField(label=ft.Text("Exam Name", style=ft.TextStyle(overflow=ft.TextOverflow.ELLIPSIS)), width=250, input_filter=ft.TextOnlyInputFilter(), col=6)
    days_text = ft.TextField(label=ft.Text("Days from Today(inc. weekends)", style=ft.TextStyle(overflow=ft.TextOverflow.ELLIPSIS)), width=120, input_filter=ft.NumbersOnlyInputFilter(), col=3)
    sheets_text = ft.TextField(label=ft.Text("Sheets", style=ft.TextStyle(overflow=ft.TextOverflow.ELLIPSIS)), width=120, input_filter=ft.NumbersOnlyInputFilter(), col=3)
    study_mins_text = ft.TextField(label=ft.Text("Total Study Mins", style=ft.TextStyle(overflow=ft.TextOverflow.ELLIPSIS)), width=250, input_filter=ft.NumbersOnlyInputFilter(), col=6)

    # Standard overlay method for notifications in Flet 1.0
    def show_notification(text: str):
        sb = ft.SnackBar(content=ft.Text(text))
        page.overlay.append(sb)
        sb.open = True
        page.update()

    def toggle_theme_mode(e):
        if page.theme_mode == ft.ThemeMode.DARK:
            page.theme_mode = ft.ThemeMode.LIGHT
        else:
            page.theme_mode = ft.ThemeMode.DARK

    async def remove_exam(row_to_remove, name_to_remove, key_to_remove):
        global exams
        # 1. Filter out the dictionary from global array
        exams = [exam for exam in exams if exam["name"] != name_to_remove]

        # 2. Remove from persistent storage
        await prefs.remove(key_to_remove)

        # 3. Safely remove the layout row from the container list
        if row_to_remove:
            exams_container.controls.remove(row_to_remove)

        show_notification(f"Removed exam: {name_to_remove}")

    async def add_exam(flash, from_inputs, exam_data=None, storage_key=None):
        today = datetime.now().date()

        if from_inputs:
            name = name_text.value.strip()
            days = days_text.value.strip()
            sheets = sheets_text.value.strip()

            if not name or not days or not sheets:
                show_notification("Please fill in all fields.")
                return

            # Calculate the explicit target date based on inputs
            target_date = (today + timedelta(days=int(days))).isoformat()
            current_days_away = int(days)
        else:
            name = exam_data["name"]
            sheets = str(exam_data["sheets"])
            target_date = exam_data["target_date"]

            # Dynamically calculate days remaining relative to today's date [2026]
            saved_date = datetime.fromisoformat(target_date).date()
            current_days_away = (saved_date - today).days

            # If the exam day passed, treat it as 0 days left (or you can filter it out)
            if current_days_away < 0:
                await remove_exam(row_to_remove=None, name_to_remove=name, key_to_remove=storage_key)
                return # STops function execution if the exam is already past

        # Append data dictionary to local array for calculations using current days remaining
        exams.append({"name": name, "days": max(current_days_away, 1), "sheets": int(sheets)})

        # Unique keys generated based on distinct names to prevent overlapping entries
        if not storage_key:
            storage_key = f"exam_list_item:{name.lower().replace(' ', '_')}"

        # Convert dict to JSON string before saving, storing the immutable target date string
        serialized_data = json.dumps({"name": name, "target_date": target_date, "sheets": int(sheets)})
        await prefs.set(storage_key, serialized_data)

        if flash:
            show_notification(f"Added exam: {name}")

        # Create structured Row element so components align horizontally
        exam_row = ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=10)
        exam_text = ft.Text(f"{name} | {current_days_away} days away | {sheets} sheets", size=16)

        # Handle deletion explicitly via an inline async wrapper to keep positional mappings safe
        async def on_del_click(e, r=exam_row, n=name, k=storage_key):
            await remove_exam(r, n, k)
        exam_del_btn = ft.IconButton(
            icon=ft.Icons.DELETE_FOREVER,
            icon_color=ft.Colors.RED_400,
            on_click=on_del_click
        )

        exam_row.controls = [exam_text, exam_del_btn]
        exams_container.controls.append(exam_row)

        # Clear fields for next addition
        if from_inputs:
            name_text.value = ""
            days_text.value = ""
            sheets_text.value = ""

        page.update()

    # Load previously saved items from SharedPreferences FIRST before building UI
    saved_keys = await prefs.get_keys("exam_list_item")
    today_date = datetime.now().date()

    for key in saved_keys:
        raw_string = await prefs.get(key)
        if raw_string:
            try:
                data = json.loads(raw_string)

                # Check fallback compatibility for older records missing target_date
                if "target_date" not in data:
                    data["target_date"] = (today_date + timedelta(days=int(data.get("days", 1)))).isoformat()

                saved_target = datetime.fromisoformat(data["target_date"]).date()
                computed_days = (saved_target - today_date).days
                display_days = max(computed_days, 0)

                # Build rows silently into memory array first
                exams.append({"name": data["name"], "days": max(computed_days, 1), "sheets": int(data["sheets"])})

                # Setup rows structure directly to container controls array
                exam_row = ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=10)
                exam_text = ft.Text(f"{data['name']} | {display_days} days away | {data['sheets']} sheets", size=16)

                current_key = key
                current_name = data["name"]

                async def on_saved_del_click(e, r=exam_row, n=current_name, k=current_key):
                    await remove_exam(r, n, k)

                exam_del_btn = ft.IconButton(
                    icon=ft.Icons.DELETE_FOREVER,
                    icon_color=ft.Colors.RED_400,
                    on_click=on_saved_del_click
                )
                exam_row.controls = [exam_text, exam_del_btn]
                exams_container.controls.append(exam_row)


            except json.JSONDecodeError:
                pass

    async def add_exam_btn_clicked(e):
        await add_exam(flash=True, from_inputs=True)

    def calculate(e):
        if not exams:
            show_notification("Please add at least one exam first.")
            return
        if not study_mins_text.value:
            show_notification("Please provide total available study minutes.")
            return

        total_sheets = sum(exam["sheets"] for exam in exams)
        if total_sheets == 0:
            show_notification("Total sheets cannot be 0.")
            return

        m_values = []
        for exam in exams:
            m_values.append(len(exams) / exam["days"] * (exam["sheets"] / total_sheets))

        m_t = sum(m_values)
        if m_t == 0:
            return

        m_c = int(study_mins_text.value) / m_t

        # Compile display results list for Modal layout output
        results_list = []
        for exam in exams:
            allocated_mins = round(m_c * m_values[exams.index(exam)])
            results_list.append(ft.Text(f"• Study {allocated_mins} mins for {exam['name']}", size=16))

        # Close action callback for modal
        def close_modal(evt):
            result_modal.open = False
            page.update()

        # Show final dynamic allocations via Flet 1.0 modal layout engine
        result_modal = ft.AlertDialog(
            title=ft.Text("Your Optimized Study Schedule"),
            content=ft.Column(controls=results_list, tight=True),
            actions=[ft.TextButton("Close", on_click=close_modal)]
        )
        page.overlay.append(result_modal)
        result_modal.open = True
        page.update()

    async def quit_app(e):
        await page.window.close()

    # UI Layout Construction using normal synchronous add() method
    page.add(
        ft.Text("Study Time", size=24, weight=ft.FontWeight.BOLD, align=ft.Alignment.TOP_CENTER),

        ft.ResponsiveRow([name_text], alignment=ft.MainAxisAlignment.CENTER),
        ft.ResponsiveRow([days_text, sheets_text], alignment=ft.MainAxisAlignment.CENTER),
        ft.ResponsiveRow(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Button(ft.Text("Add Exam", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS), icon=ft.Icons.ADD, on_click=add_exam_btn_clicked, col=6,
                  style=ft.ButtonStyle(
                    # radius=5 makes it slightly rounded but keeps a clean grid feel
                    shape=ft.RoundedRectangleBorder(radius=5),
                    # Set your custom font size here
                    text_style=ft.TextStyle(size=18, weight=ft.FontWeight.W_500)
                ),
                          ),
                ]
        ),

        exams_container,
        ft.Divider(height=20, thickness=1),
        ft.ResponsiveRow([study_mins_text], alignment=ft.MainAxisAlignment.CENTER),
        ft.ResponsiveRow(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Button(ft.Text("Split", style=ft.TextStyle(overflow=ft.TextOverflow.ELLIPSIS, size=14)), icon=ft.Icons.CALCULATE, on_click=calculate,
                          bgcolor=ft.Colors.BLUE_900, color=ft.Colors.WHITE, col=3,
                          style=ft.ButtonStyle(
                    # radius=5 makes it slightly rounded but keeps a clean grid feel
                    shape=ft.RoundedRectangleBorder(radius=5),
                    # Set your custom font size here
                    text_style=ft.TextStyle(size=page.width * 0.01, weight=ft.FontWeight.W_500)
                ),
                      ),

                ft.Button("Toggle Theme", on_click=toggle_theme_mode, bgcolor=ft.Colors.RED_400, color=ft.Colors.WHITE, col=3,
                  style=ft.ButtonStyle(
                      # radius=5 makes it slightly rounded but keeps a clean grid feel
                      shape=ft.RoundedRectangleBorder(radius=5),
                      # Set your custom font size here
                      text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_500)
                  )
                  ),


            ]

        )
    )



if __name__ == "__main__":
    ft.run(main)
