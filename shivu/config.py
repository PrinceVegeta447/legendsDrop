class Config(object):
    LOGGER = True

    # Get this value from my.telegram.org/apps
    OWNER_ID = "1710597756"
    sudo_users = [1710597756]
    GROUP_ID = -1002415126626
    TOKEN = "7804712218:AAGhfhfsRLASlMV5uybHFeuj3NmAKpXTR4E"
    mongo_url = "mongodb+srv://vegetakun447:1jPSDznTX6gy7Nqr@cluster0.hcngy.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    PHOTO_URL = ["https://telegra.ph/file/b925c3985f0f325e62e17.jpg", "https://telegra.ph/file/4211fb191383d895dab9d.jpg"]
    SUPPORT_CHAT = "Collect_em_support"
    UPDATE_CHAT = "Collect_em_support"
    BOT_USERNAME = "@pelpal669bot"
    CHARA_CHANNEL_ID = "-1002431614358"
    api_id = 26626068
    api_hash = "bf423698bcbe33cfd58b11c78c42caa2"

    
class Production(Config):
    LOGGER = True


class Development(Config):
    LOGGER = True
