"""
Scheduler Events for App Migrator
"""


def get_events():
    """
    Return scheduler events for the app
    """
    return {
        # "hourly": [
        #     "app_migrator.tasks.hourly_cleanup"
        # ],
        # "daily": [
        #     "app_migrator.tasks.daily_maintenance"
        # ],
        # "weekly": [
        #     "app_migrator.tasks.weekly_report"
        # ]
    }


print("✓ Scheduler events module loaded")
