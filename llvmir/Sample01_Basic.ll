; ModuleID = "java_Sample01_Basic"
target triple = "x86_64-pc-linux-gnu"
target datalayout = ""

define i32 @"factorial"(i32 %"n")
{
entry:
  %"result" = alloca i32
  %"i" = alloca i32
  store i32 1, i32* %"result"
  store i32 2, i32* %"i"
  br label %"loop"
loop:
  %"i_val" = load i32, i32* %"i"
  %"cond" = icmp sle i32 %"i_val", %"n"
  br i1 %"cond", label %"body", label %"exit"
exit:
  %"final" = load i32, i32* %"result"
  ret i32 %"final"
body:
  %".7" = load i32, i32* %"result"
  %"new_result" = mul i32 %".7", %"i_val"
  store i32 %"new_result", i32* %"result"
  %"new_i" = add i32 %"i_val", 1
  store i32 %"new_i", i32* %"i"
  br label %"loop"
}

define double @"sumArray"(i32* %"arr", i32 %"len")
{
entry:
  ret double              0x0
}
