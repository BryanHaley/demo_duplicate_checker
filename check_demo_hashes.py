import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime
import wx
import re
import os
import sys
import hashlib

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# The ID and range of a sample spreadsheet.
SPREADSHEET_ID = "1aHA6yjXxiYmiJkPLHyKPt8Hv2V0auiqO9vgSg9JEuZg"
RANGE_NAME = "A2:ZZZ100000"

def get_sheet():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    try:
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()
        return sheet
    except HttpError as err:
        print(err)
    return None

def get_hashes(sheet, sheet_name):
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    try:
        # Call the Sheets API
        result = (
            sheet.values()
            .get(spreadsheetId=SPREADSHEET_ID, range=sheet_name + '!' + RANGE_NAME)
            .execute()
        )
        values = result.get("values", [])
        if not values:
            print("No data found.")
        return values
    except HttpError as err:
        print(err)

def insert_row(sheet, sheet_name, row):
    try:
        # Call the Sheets API
        result = (
            sheet.values().
            append(
                spreadsheetId=SPREADSHEET_ID,
                range=sheet_name + '!' + RANGE_NAME,
                valueInputOption='RAW',   # or 'USER_ENTERED'
                insertDataOption='INSERT_ROWS',
                body={
                    'values': [row]
                }
            )
            .execute()
        )
        print(result)
    except HttpError as err:
        print(err)

def get_hash_from_file(filepath):
    file_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            file_hash.update(chunk)
    return file_hash.hexdigest()
    

def get_hashes_from_folder(dir):
    files = [os.path.join(dir, x) for x in os.listdir(dir) if os.path.splitext(x)[1].lower() == '.dem']
    hashes = []
    for file in files:
        hashes += [get_hash_from_file(file)]
    return hashes


class RunInfoDialog(wx.Dialog):
    def __init__(self, parent, title="Enter Run Information"):
        super().__init__(parent, title=title, size=(500, 200))
        
        # Panel and Sizer
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Name field
        name_box = wx.BoxSizer(wx.HORIZONTAL)
        name_label = wx.StaticText(panel, label="Runner: ")
        self.name_ctrl = wx.TextCtrl(panel)
        name_box.Add(name_label, flag=wx.RIGHT, border=8)
        name_box.Add(self.name_ctrl, proportion=1)
        vbox.Add(name_box, flag=wx.EXPAND | wx.ALL, border=10)

        # Dropdown for run type
        dropdown_box = wx.BoxSizer(wx.HORIZONTAL)
        dropdown_label = wx.StaticText(panel, label="Run Type: ")
        self.run_types = [
            "WON Scriptless",
            "WON Scripted",
            "Steam Scriptless",
            "Steam Scripted",
            "Other"
        ]
        self.dropdown = wx.Choice(panel, choices=self.run_types)
        self.dropdown.SetSelection(0)  # default to first option
        dropdown_box.Add(dropdown_label, flag=wx.RIGHT, border=8)
        dropdown_box.Add(self.dropdown, proportion=1)
        vbox.Add(dropdown_box, flag=wx.EXPAND | wx.ALL, border=10)

        # Folder field with browse button
        folder_box = wx.BoxSizer(wx.HORIZONTAL)
        folder_label = wx.StaticText(panel, label="Demo Files Directory: ")
        default_folder = ""
        if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
            if os.path.isfile(sys.argv[1]):
                default_folder = os.path.dirname(sys.argv[1])
            else:
                default_folder = sys.argv[1]
        self.folder_ctrl = wx.TextCtrl(panel, value=default_folder)
        browse_button = wx.Button(panel, label="Browse")
        browse_button.Bind(wx.EVT_BUTTON, self.on_browse)

        folder_box.Add(folder_label, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=8)
        folder_box.Add(self.folder_ctrl, proportion=1, flag=wx.RIGHT, border=5)
        folder_box.Add(browse_button)
        vbox.Add(folder_box, flag=wx.EXPAND | wx.ALL, border=10)

        # Buttons
        hbox_buttons = wx.BoxSizer(wx.HORIZONTAL)
        ok_button = wx.Button(panel, wx.ID_OK, label="OK")
        cancel_button = wx.Button(panel, wx.ID_CANCEL, label="Cancel")
        hbox_buttons.Add(ok_button)
        hbox_buttons.Add(cancel_button, flag=wx.LEFT, border=5)
        vbox.Add(hbox_buttons, flag=wx.ALIGN_CENTER | wx.ALL, border=10)

        panel.SetSizer(vbox)

    def get_values(self):
        name = self.name_ctrl.GetValue()
        dir = self.folder_ctrl.GetValue()
        run_type = self.run_types[self.dropdown.GetSelection()]
        return name, dir, run_type
    
    def on_browse(self, event):
        dlg = wx.DirDialog(self, "Choose a directory", style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            self.folder_ctrl.SetValue(dlg.GetPath())
        dlg.Destroy()


class MyApp(wx.App):
    def OnInit(self):
        dialog = RunInfoDialog(None)
        if dialog.ShowModal() == wx.ID_OK:
            name, dir, run_type = dialog.get_values()
            if not name or not run_type or not dir:
                wx.MessageBox("Please enter a name, time, and directory.", "Warning", wx.CANCEL | wx.ICON_WARNING)
                return False
            if not os.path.exists(dir) and (not os.path.isfile(dir)):
                wx.MessageBox("Directory to demo files is invalid.", "Warning", wx.CANCEL | wx.ICON_WARNING)
                return False
            else:
                this_run_hashes = get_hashes_from_folder(dir)
                this_run_row = [name, datetime.now().strftime("%Y-%m-%d")] + this_run_hashes
                sheet = get_sheet()
                sheet_hashes = get_hashes(sheet, run_type)
                if len(sheet_hashes) < 1:
                    wx.MessageBox("No runs to compare against. Submitting hashes to sheet.", "Info", wx.OK | wx.ICON_INFORMATION)
                    insert_row(sheet, run_type, this_run_row)
                else:
                    found_in_hashes = False
                    for i, this_run_hash in enumerate(this_run_hashes):
                        if found_in_hashes:
                            continue
                        for row in sheet_hashes:
                            if this_run_hash in row:
                                wx.MessageBox(f"Submitted demo {i+1} is the same as a demo from {row[0]}'s run checked on {row[1]}.", "Warning", wx.CANCEL | wx.ICON_WARNING)
                                found_in_hashes = True
                                continue
                    if not found_in_hashes:
                        wx.MessageBox("No conflicts.", "Info", wx.OK | wx.ICON_INFORMATION)
                        insert_row(sheet, run_type, this_run_row)
        dialog.Destroy()
        return True

if __name__ == "__main__":
    app = MyApp()
    app.MainLoop()

