Attribute VB_Name = "CachexiaUI"
Option Explicit

Private Const UI_SHEET As String = "Mock UI"
Private Const REVIEW_SHEET As String = "Clinical Review"

Public Sub InitializeMockUI()
    UpdateInputGuidance
    ConfigureLungSubtypeField
End Sub

Public Sub UpdateInputGuidance()
    Dim ui As Worksheet
    Set ui = ThisWorkbook.Worksheets(UI_SHEET)

    With ui
        .Range("D9").Value = "Required date. Records after this date cannot be predictors."
        .Range("D10").Value = "Required whole number: 18 to 95 years."
        .Range("D11").Value = "Valid: female, male or unknown."
        .Range("D12").Value = "Required confirmed cancer type from the dropdown."
        .Range("D14").Value = "Valid: I, II, III, IV or unknown."
        .Range("D15").Value = "Required: 140 to 200 cm."
        .Range("D16").Value = "Valid: 0, 1, 2, 3, 4 or unknown."
        .Range("D17").Value = "Valid: yes, no or unknown/not documented."
        .Range("D18").Value = "yes=documented; no=assessed and absent; unknown=not assessed/documented."
    End With

    UpdateSubtypeGuidance
End Sub

Public Sub UpdateSubtypeGuidance()
    Dim ui As Worksheet
    Set ui = ThisWorkbook.Worksheets(UI_SHEET)

    If LCase$(Trim$(CStr(ui.Range("C12").Value))) = "lung" Then
        ui.Range("D13").Value = "Required for lung: SCLC, NSCLC or unknown."
    Else
        ui.Range("D13").Value = "Must be not applicable unless cancer type is lung."
    End If
End Sub

Public Sub ConfigureLungSubtypeField()
    Dim ui As Worksheet
    Dim cancerType As String
    Dim subtype As String

    Set ui = ThisWorkbook.Worksheets(UI_SHEET)
    cancerType = LCase$(Trim$(CStr(ui.Range("C12").Value)))
    subtype = LCase$(Trim$(CStr(ui.Range("C13").Value)))

    On Error GoTo CleanUp
    Application.EnableEvents = False

    With ui.Range("C13").Validation
        .Delete
        .Add Type:=xlValidateList, AlertStyle:=xlValidAlertStop, _
            Operator:=xlBetween, _
            Formula1:="=INDIRECT(IF($C$12=""lung"",""LungSubtypeValues"",""NonLungSubtypeValues""))"
        .IgnoreBlank = False
        .InCellDropdown = True
        .InputTitle = "Lung subtype"
        .InputMessage = "SCLC, NSCLC or unknown for lung; otherwise not applicable."
        .ErrorTitle = "Invalid subtype"
        .ErrorMessage = "Choose a value permitted for the selected cancer type."
        .ShowInput = True
        .ShowError = True
    End With

    If cancerType = "lung" Then
        If subtype <> "sclc" And subtype <> "nsclc" And subtype <> "unknown" Then
            ui.Range("C13").Value = "unknown"
        End If
    Else
        ui.Range("C13").Value = "not applicable"
    End If

    UpdateSubtypeGuidance

CleanUp:
    Application.EnableEvents = True
End Sub

Public Sub CalculateRisk()
    Dim ui As Worksheet
    Set ui = ThisWorkbook.Worksheets(UI_SHEET)

    InitializeMockUI

    If Not IsDate(ui.Range("C9").Value) Then
        MsgBox "Enter a valid prediction date.", vbExclamation, "Missing prediction date"
        ui.Range("C9").Select
        Exit Sub
    End If

    If Not IsNumeric(ui.Range("C10").Value) Or ui.Range("C10").Value < 18 Or ui.Range("C10").Value > 95 Then
        MsgBox "Enter an age from 18 to 95 years.", vbExclamation, "Invalid age"
        ui.Range("C10").Select
        Exit Sub
    End If

    If Not IsNumeric(ui.Range("C15").Value) Or ui.Range("C15").Value < 140 Or ui.Range("C15").Value > 200 Then
        MsgBox "Enter a height from 140 to 200 cm.", vbExclamation, "Invalid height"
        ui.Range("C15").Select
        Exit Sub
    End If

    Application.CalculateFull

    If ThisWorkbook.Worksheets("Engine").Range("B13").Value = "" Then
        MsgBox "Add at least two valid dated weights on or before the prediction date. Future weights are excluded from predictors.", vbExclamation, "Weight history required"
        Exit Sub
    End If

    MsgBox "Synthetic outputs recalculated." & vbCrLf & vbCrLf & _
        "These results are simulation assumptions and must not be used for clinical decisions.", _
        vbInformation, "Research-only result"
End Sub

Public Sub ResetForm()
    Dim ui As Worksheet
    Set ui = ThisWorkbook.Worksheets(UI_SHEET)

    With ui
        .Range("C9:C17").ClearContents
        .Range("B24:C33").ClearContents
        .Range("C11").Value = "unknown"
        .Range("C12").Value = "other solid tumour"
        .Range("C14").Value = "unknown"
        .Range("C16:C17").Value = "unknown"
        .Range("C18").Value = "unknown"
        .Range("C9").Select
    End With

    InitializeMockUI
    Application.CalculateFull
End Sub

Public Sub LoadLowRiskExample()
    Dim ui As Worksheet
    Set ui = ThisWorkbook.Worksheets(UI_SHEET)

    With ui
        .Range("C9").Value = DateSerial(2026, 1, 31)
        .Range("C10").Value = 48
        .Range("C11").Value = "female"
        .Range("C12").Value = "breast"
        .Range("C13").Value = "not applicable"
        .Range("C14").Value = "I"
        .Range("C15").Value = 164
        .Range("C16").Value = "0"
        .Range("C17").Value = "no"
        .Range("C18").Value = "unknown"
        .Range("B24:C33").ClearContents
        .Range("B24").Value = DateSerial(2025, 7, 31)
        .Range("C24").Value = 66
        .Range("B25").Value = DateSerial(2026, 1, 31)
        .Range("C25").Value = 65.5
    End With

    InitializeMockUI
    Application.CalculateFull
End Sub

Public Sub LoadHighRiskExample()
    Dim ui As Worksheet
    Set ui = ThisWorkbook.Worksheets(UI_SHEET)

    With ui
        .Range("C9").Value = DateSerial(2026, 1, 31)
        .Range("C10").Value = 72
        .Range("C11").Value = "male"
        .Range("C12").Value = "pancreatic"
        .Range("C13").Value = "not applicable"
        .Range("C14").Value = "IV"
        .Range("C15").Value = 176
        .Range("C16").Value = "3"
        .Range("C17").Value = "yes"
        .Range("C18").Value = "unknown"
        .Range("B24:C33").ClearContents
        .Range("B24").Value = DateSerial(2025, 7, 31)
        .Range("C24").Value = 74
        .Range("B25").Value = DateSerial(2026, 1, 31)
        .Range("C25").Value = 68.8
    End With

    InitializeMockUI
    Application.CalculateFull
End Sub

Public Sub OpenClinicalReview()
    ThisWorkbook.Worksheets(REVIEW_SHEET).Activate
End Sub

Public Sub OpenMockUI()
    ThisWorkbook.Worksheets(UI_SHEET).Activate
End Sub
