class Config(object):
    LOGGER = True

    # Get this value from my.telegram.org/apps
    OWNER_ID = "1710597756"
    sudo_users = [1710597756]
    GROUP_ID = -1002483506913
    TOKEN = "7568918921:AAHT6_qx76-7hyG74S2T0eG1R1yWgqzXmWo"
    mongo_url = "mongodb+srv://vegetakun447:TK1WRYfAESFT5vTe@cluster0.hcngy.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
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
