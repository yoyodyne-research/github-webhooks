# import requests
import shotgun_api3

# base_url = "https://thr3dcgi-staging.shotgunstudio.com" 
# r = requests.get("https://api.github.com/orgs/yoyodyne-research/actions/secrets/SCRIPT_NAME")
# print(r.json())
#api_key = requests.get("https://api.github.com/orgs/yoyodyne-research/actions/secrets/API_KEY")

class ShotgunHandler(object):
  """
  Small class to store the Shotgun API handle.
  """
  _sg = None

  @classmethod
  def get_conn(cls):
      """
      :return: Shotgun API handle
      """
      if not ShotgunHandler._sg:
          ShotgunHandler._sg = shotgun_api3.Shotgun(
              base_url,
              os.environ.get("SCRIPT_NAME"),
              os.environ.get("API_KEY")
          )

      return ShotgunHandler._sg


def test_hello():
  print("hello.")

def test_context():
  print(shotgun_api3)
