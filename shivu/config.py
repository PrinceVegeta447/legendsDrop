class Config(object):
    LOGGER = True

    # Get this value from my.telegram.org/apps
    OWNER_ID = "1710597756"
    sudo_users = [1710597756]
    GROUP_ID = -1002415126626
    TOKEN = "7586298589:AAHNpgN-iWCazr_yYR4XFANCRfpH4ILl4qg"
    mongo_url = "mongodb+srv://vegetakun447:1jPSDznTX6gy7Nqr@cluster0.hcngy.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    PHOTO_URL = ["https://telegra.ph/file/b925c3985f0f325e62e17.jpg", "https://telegra.ph/file/4211fb191383d895dab9d.jpg"]
    SUPPORT_CHAT = "CollectYourLegends"
    UPDATE_CHAT = "CollectYourLegends"
    BOT_USERNAME = "@LegendsDropBot"
    CHARA_CHANNEL_ID = "-1002431614358"
    api_id = 26626068
    api_hash = "bf423698bcbe33cfd58b11c78c42caa2"

    
class Production(Config):
    LOGGER = True


class Development(Config):
    LOGGER = True
