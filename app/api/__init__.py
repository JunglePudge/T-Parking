from . import home, auth, register, profile, parking

routers = [
    home.router,
    auth.router,
    register.router,
    profile.router,
    parking.router,
]
