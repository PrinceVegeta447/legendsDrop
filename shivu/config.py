class Config(object):
    LOGGER = True

    # Get this value from my.telegram.org/apps
    OWNER_ID = "1710597756"
    sudo_users = [1710597756]
    GROUP_ID = -1002483506913
    TOKEN = "7586298589:AAHRWxAAs6pLzf4bnZ9t3JAdD7cPRWTUE8g"
    mongo_url = "mongodb+srv://vegetakun447:1jPSDznTX6gy7Nqr@cluster0.hcngy.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    PHOTO_URL = ["http://ibb.co/WvZ6gLTr"]
    SUPPORT_CHAT = "CollectYourLegends"
    UPDATE_CHAT = "CollectYourLegends"
    BOT_USERNAME = "LegendsDropBot"
    CHARA_CHANNEL_ID = "-1002431614358"
    api_id = 26626068
    api_hash = "bf423698bcbe33cfd58b11c78c42caa2"
    LOAN_CHANNEL_ID = "-1002366254495"
    
class Production(Config):
    LOGGER = True


class Development(Config):
    LOGGER = True
