from uuid import UUID

# dummy user data using models.User
users = [
    {
        "id": UUID(int=1),
        "name": "Alice",
        "email": "w5Tqz@example.com",
        "created_at": "2022-01-01T00:00:00",
    },
    {
        "id": UUID(int=2),
        "name": "Bob",
        "email": "w5Tqz@example.com",
        "created_at": "2022-01-01T00:00:00",
    },
    {
        "id": UUID(int=3),
        "name": "Charlie",
        "email": "w5Tqz@example.com",
        "created_at": "2022-01-01T00:00:00",
    },
    {
        "id": UUID(int=4),
        "name": "David",
        "email": "w5Tqz@example.com",
        "created_at": "2022-01-01T00:00:00",
    },
    {
        "id": UUID(int=5),
        "name": "Eve",
        "email": "w5Tqz@example.com",
        "created_at": "2022-01-01T00:00:00",
    },
    {
        "id": UUID(int=6),
        "name": "Frank",
        "email": "w5Tqz@example.com",
        "created_at": "2022-01-01T00:00:00",
    },
    {
        "id": UUID(int=7),
        "name": "Grace",
        "email": "w5Tqz@example.com",
        "created_at": "2022-01-01T00:00:00",
    },
    {
        "id": UUID(int=8),
        "name": "Hank",
        "email": "w5Tqz@example.com",
        "created_at": "2022-01-01T00:00:00",
    },
    {
        "id": UUID(int=9),
        "name": "Ivy",
        "email": "w5Tqz@example.com",
        "created_at": "2022-01-01T00:00:00",
    },
    {
        "id": UUID(int=10),
        "name": "Jack",
        "email": "w5Tqz@example.com",
        "created_at": "2022-01-01T00:00:00",
    },
]


# dummy tasks mapping against a few users to models.Task
tasks = [
    {
        "id": UUID(int=101),
        "user_id": UUID(int=1),
        "title": "Task 1",
        "priority": 1,
        "created_at": "2022-01-01T00:00:00",
    },
    {
        "id": UUID(int=102),
        "user_id": UUID(int=1),
        "title": "Task 2",
        "priority": 2,
        "created_at": "2022-01-01T00:00:00",
    },
    {
        "id": UUID(int=103),
        "user_id": UUID(int=1),
        "title": "Task 3",
        "priority": 3,
        "created_at": "2022-01-01T00:00:00",
    },
    {
        "id": UUID(int=104),
        "user_id": UUID(int=2),
        "title": "Task 4",
        "priority": 1,
        "created_at": "2022-01-01T00:00:00",
    },
    {
        "id": UUID(int=105),
        "user_id": UUID(int=2),
        "title": "Task 5",
        "priority": 2,
        "created_at": "2022-01-01T00:00:00",
    },
    {
        "id": UUID(int=106),
        "user_id": UUID(int=2),
        "title": "Task 6",
        "priority": 3,
        "created_at": "2022-01-01T00:00:00",
    },
]
