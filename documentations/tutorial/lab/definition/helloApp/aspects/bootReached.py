aspects = [
    {
        "file": "src/app.js",
        "aspects": [
            {
                "pointcut": "function boot() {",
                "advice": "  console.log('[device] boot reached');",
                "position": "after",
                "trim-advice": False
            }
        ]
    }
]

