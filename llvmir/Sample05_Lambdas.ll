; ModuleID = "java_Sample05_Lambdas"
target triple = "x86_64-pc-linux-gnu"
target datalayout = ""

%"Shape" = type {i8*, i8*}
%"ArrayList" = type {i8**, i32, i32}
%"Lambda_closure" = type {i8*, i8*}
define i32 @"lambda_add"(i8* %".1", i32 %".2", i32 %".3")
{
entry:
  %".5" = add i32 %".2", %".3"
  ret i32 %".5"
}
