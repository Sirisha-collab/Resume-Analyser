# -----------------------
# Skill Gap Roadmap
# -----------------------

LEARNING_RESOURCES = {
    "python": {
        "resources": [
            {"name": "Python for Everybody (Coursera)", "url": "https://www.coursera.org/specializations/python"},
            {"name": "Python Bootcamp (Udemy)", "url": "https://www.udemy.com/course/complete-python-bootcamp/"},
            {"name": "Python Learning Path (Microsoft Learn)", "url": "https://learn.microsoft.com/en-us/training/paths/python-language/"},
        ],
        "projects": [
            "CLI tool that parses and reports on a real file format",
            "REST API with FastAPI, tests, and a Dockerfile",
        ],
    },

    "machine learning": {
        "resources": [
            {"name": "Machine Learning - Andrew Ng (Coursera)", "url": "https://www.coursera.org/learn/machine-learning"},
            {"name": "Machine Learning A-Z (Udemy)", "url": "https://www.udemy.com/course/machinelearning/"},
        ],
        "projects": [
            "Build a churn prediction model",
            "Customer segmentation using K-Means",
            "End-to-end ML pipeline with deployment (FastAPI + Docker)",
        ],
    },

    "deep learning": {
        "resources": [
            {"name": "Deep Learning Specialization (Coursera)", "url": "https://www.coursera.org/specializations/deep-learning"},
            {"name": "Deep Learning (Udemy)", "url": "https://www.udemy.com/course/deeplearning/"},
        ],
        "projects": [
            "Fine-tune a pretrained transformer on a domain dataset",
            "Image classifier with transfer learning and a served endpoint",
        ],
    },

    "javascript": {
        "resources": [
            {"name": "JavaScript Course (Udemy)", "url": "https://www.udemy.com/course/the-complete-javascript-course/"},
            {"name": "JavaScript Path (Microsoft Learn)", "url": "https://learn.microsoft.com/en-us/training/paths/javascript-first-steps/"},
            {"name": "JavaScript Reference (MDN)", "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript"},
        ],
    },

    "typescript": {
        "resources": [
            {"name": "TypeScript Handbook (Official Docs)", "url": "https://www.typescriptlang.org/docs/handbook/intro.html"},
            {"name": "Understanding TypeScript (Udemy)", "url": "https://www.udemy.com/course/understanding-typescript/"},
        ],
        "projects": [
            "Convert an existing JS project to strict-mode TypeScript",
        ],
    },

    "react": {
        "resources": [
            {"name": "React Course (Udemy)", "url": "https://www.udemy.com/course/react-the-complete-guide/"},
            {"name": "React Docs", "url": "https://react.dev"},
            {"name": "React Learn Path", "url": "https://react.dev/learn"},
        ],
    },

    "angular": {
        "resources": [
            {"name": "Angular Docs (Official)", "url": "https://angular.dev"},
            {"name": "Angular Tutorials (Official)", "url": "https://angular.dev/tutorials"},
            {"name": "Angular - The Complete Guide (Udemy)", "url": "https://www.udemy.com/course/the-complete-guide-to-angular-2/"},
        ],
        "projects": [
            "CRUD dashboard with reactive forms and route guards",
        ],
        "tools": ["Angular CLI", "RxJS", "NgRx"],
    },

    "html": {
        "resources": [
            {"name": "HTML Reference (MDN)", "url": "https://developer.mozilla.org/en-US/docs/Web/HTML"},
            {"name": "Learn HTML (web.dev)", "url": "https://web.dev/learn/html/"},
            {"name": "Responsive Web Design (freeCodeCamp)", "url": "https://www.freecodecamp.org/learn/responsive-web-design/"},
        ],
        "projects": [
            "Rebuild a landing page using semantic elements and pass an accessibility audit",
        ],
    },

    "css": {
        "resources": [
            {"name": "CSS - The Complete Guide (Udemy)", "url": "https://www.udemy.com/course/css-the-complete-guide-incl-flexbox-grid-sass/"},
            {"name": "Web Design with HTML & CSS (Coursera)", "url": "https://www.coursera.org/learn/html-css-javascript-for-web-developers"},
            {"name": "CSS Basics (MDN Docs)", "url": "https://developer.mozilla.org/en-US/docs/Web/CSS"},
        ],
    },

    "git": {
        "resources": [
            {"name": "Pro Git Book (Free, Official)", "url": "https://git-scm.com/book/en/v2"},
            {"name": "Git Learn Hub (git-scm.com)", "url": "https://git-scm.com/learn"},
            {"name": "Learn Git Branching (Interactive)", "url": "https://learngitbranching.js.org/"},
        ],
        "projects": [
            "Rewrite a messy feature branch with interactive rebase",
            "Resolve a real merge conflict across three commits",
            "Set up a branching strategy and PR template for one of your repos",
        ],
        "tools": ["git rebase -i", "git bisect", "git stash", "GitHub Actions"],
    },

    "graphql": {
        "resources": [
            {"name": "Introduction to GraphQL (Official)", "url": "https://graphql.org/learn/"},
            {"name": "How to GraphQL (Fullstack Tutorial)", "url": "https://www.howtographql.com/"},
            {"name": "Apollo Odyssey Tutorials", "url": "https://graphql.com/tutorials/"},
            {"name": "Apollo GraphQL Docs", "url": "https://www.apollographql.com/docs/"},
        ],
        "projects": [
            "Wrap an existing REST endpoint in a GraphQL schema with resolvers",
            "Add pagination and field-level auth to a GraphQL API",
            "Fix an N+1 resolver problem with DataLoader",
        ],
        "tools": ["Apollo Server", "Apollo Client", "GraphQL Playground", "DataLoader"],
    },

    "node.js": {
        "resources": [
            {"name": "Node.js Learn (Official)", "url": "https://nodejs.org/en/learn"},
            {"name": "Node.js - The Complete Guide (Udemy)", "url": "https://www.udemy.com/course/nodejs-the-complete-guide/"},
        ],
        "projects": [
            "Build an Express API with auth middleware and integration tests",
        ],
    },

    "azure": {
        "resources": [
            {"name": "Azure Fundamentals (Microsoft Learn)", "url": "https://learn.microsoft.com/en-us/training/paths/azure-fundamentals/"},
            {"name": "Azure Course (Udemy)", "url": "https://www.udemy.com/course/azure-essentials/"},
        ],
        "tools": ["Azure ML", "Azure Functions", "AKS", "Service Bus"],
        "projects": [
            "Deploy a containerized API to Azure App Service with CI/CD",
        ],
    },

    "java": {
        "resources": [
            {"name": "Java Programming Masterclass (Udemy)", "url": "https://www.udemy.com/course/java-the-complete-java-developer-course/"},
            {"name": "Java Programming (Coursera)", "url": "https://www.coursera.org/specializations/java-programming"},
            {"name": "Java Basics (Microsoft Learn)", "url": "https://learn.microsoft.com/en-us/training/paths/java-first-steps/"},
        ],
    },

    "csharp": {
        "resources": [
            {"name": "C# Basics for Beginners (Udemy)", "url": "https://www.udemy.com/course/csharp-tutorial-for-beginners/"},
            {"name": ".NET C# Programming (Coursera)", "url": "https://www.coursera.org/learn/csharp-programming"},
            {"name": "C# Learning Path (Microsoft Learn)", "url": "https://learn.microsoft.com/en-us/training/paths/csharp-first-steps/"},
        ],
    },

    "sql": {
        "resources": [
            {"name": "SQL for Data Science (Coursera)", "url": "https://www.coursera.org/learn/sql-for-data-science"},
            {"name": "SQL Bootcamp (Udemy)", "url": "https://www.udemy.com/course/the-complete-sql-bootcamp/"},
        ],
        "projects": [
            "Rewrite a slow query using an execution plan and an index",
        ],
    },
}