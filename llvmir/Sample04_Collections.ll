; ModuleID = "java_Sample04_Collections"
target triple = "x86_64-pc-linux-gnu"
target datalayout = ""

%"Shape" = type {i8*, i8*}
%"ArrayList" = type {i8**, i32, i32}
define void @"ArrayList_add"(%"ArrayList"* %".1", i8* %".2")
{
entry:
  ret void
}

define i8* @"ArrayList_get"(%"ArrayList"* %".1", i32 %".2")
{
entry:
  ret i8* null
}
