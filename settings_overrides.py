DBCONN = {'user':'grafana_user',
          'password':'Pajatso1',
          'host':'127.0.0.1',
          'database':'trading',
          }
TAOSTATS_API_KEY = 'tao-ec7e641a-ebab-4102-a174-1c4bb8876a2c:9d80d6cb'
DISCORD_AUTH_TOKEN = 'replacethis:string'
SEND_NOTIFICATIONS = False


try:
    from settings_overrides import *
except:
    pass
