import requests
import shotgun_api3

response = requests.get("https://api.github.com/orgs/yoyodyne-research/actions/secrets/SCRIPT_NAME")
print(response.status)
#api_key = requests.get("https://api.github.com/orgs/yoyodyne-research/actions/secrets/API_KEY")

# class ShotgunHandler(object):
#   """
#   Small class to store the Shotgun API handle.
#   """
#   _sg = None

#   @classmethod
#   def get_conn(cls):
#       """
#       :return: Shotgun API handle
#       """
#       if not ShotgunHandler._sg:
#           ShotgunHandler._sg = shotgun_api3.Shotgun(
#               APP_SETTINGS["SG_SERVER_URL"],
#               APP_SETTINGS["SG_SCRIPT_NAME"],
#               APP_SETTINGS["SG_API_KEY"]
#           )

#       return ShotgunHandler._sg
    
    
def test_hello():
  print("hello.")

def test_context():
  print(shotgun_api3)
