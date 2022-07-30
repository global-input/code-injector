aspects = [
    {
        "file": "sample.js",
        "aspects": [
            {
                "pointcut": '''            
                    let a = 5;
                ''',
                "advice": '''            
                    console.log('Assigned a to 5')
                ''',
                "position": "after"
            },
            {
                "pointcut": '''            
                    let b = 10;
                ''',
                "advice": '''            
                    console.log('About to assign b to 10')
                ''',
                "position": "before"
            },
        ]
    },
]
