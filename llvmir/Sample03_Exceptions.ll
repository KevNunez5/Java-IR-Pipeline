; ModuleID = "java_Sample03_Exceptions"
target triple = "x86_64-pc-linux-gnu"
target datalayout = ""

%"Shape" = type {i8*, i8*}
define i32 @"divide"(i32 %"a", i32 %"b")
{
entry:
  %".4" = icmp eq i32 %"b", 0
  br i1 %".4", label %"throw", label %"ok"
ok:
  %"result" = sdiv i32 %"a", %"b"
  ret i32 %"result"
throw:
  ret i32 -1
}
