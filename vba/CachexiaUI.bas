Attribute VB_Name = "CachexiaUI"
Option Explicit

Private Const UI_SHEET As String = "Mock UI"
Private Const REVIEW_SHEET As String = "Clinical Review"

Public Sub CalculateRisk()
    Dim ui As Worksheet
    Set ui = ThisWorkbook.Worksheets(UI_SHEET)

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

    Application.CalculateFull
End Sub

Public Sub OpenClinicalReview()
    ThisWorkbook.Worksheets(REVIEW_SHEET).Activate
End Sub

Public Sub OpenMockUI()
    ThisWorkbook.Worksheets(UI_SHEET).Activate
End Sub
