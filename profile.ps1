function flask {
    param([string]$command)
    $pythonPath = "C:\Users\Chanagouda S Patil\AppData\Local\Programs\Python\Python313\python.exe"
    & $pythonPath -m flask $command
}

function python {
    param([string]$command)
    $pythonPath = "C:\Users\Chanagouda S Patil\AppData\Local\Programs\Python\Python313\python.exe"
    & $pythonPath $command
}
