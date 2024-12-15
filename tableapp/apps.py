from django.apps import AppConfig

class TableappConfig(AppConfig):
    name = 'tableapp'

    def ready(self):
        import tableapp.tasks  # โหลด task ในแอป
