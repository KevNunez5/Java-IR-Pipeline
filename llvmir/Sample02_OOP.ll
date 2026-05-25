; ModuleID = "java_Sample02_OOP"
target triple = "x86_64-pc-linux-gnu"
target datalayout = ""

%"Shape" = type {i8*, i8*}
define double @"Circle_area"(%"Shape"* %".1")
{
entry:
  ret double 0x4053a27ef9db22d1
}

define double @"Rectangle_area"(%"Shape"* %".1")
{
entry:
  ret double 0x4038000000000000
}
