Attribute VB_Name = "Sheet1"
Option Explicit

Private Sub Worksheet_Change(ByVal Target As Range)
    If Intersect(Target, Me.Range("C12")) Is Nothing Then Exit Sub
    ConfigureLungSubtypeField
End Sub
