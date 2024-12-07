from datetime import datetime

import pytz


class Serializer:
    APIHeader = {
        "Responsibility": "SELF_SERVICE_PURCHASING_5",
        "RespApplication": "ICX",
        "SecurityGroup": "STANDARD",
        "NLSLanguage": "AMERICAN",
    }

    def serialize(self, values):
        raise NotImplementedError

    def format_date(self, date):
        return date.strftime("%Y-%m-%dT%H:%M:%S")

    @classmethod
    def timeit(cls) -> str:
        # Get the current UTC time
        utc_now = datetime.utcnow()

        # Convert UTC time to BDT time
        bdt_timezone = pytz.timezone("Asia/Dhaka")
        bdt_now = utc_now.replace(tzinfo=pytz.utc).astimezone(bdt_timezone)

        # Format BDT time as a string
        bdt_time_str = bdt_now.strftime("%Y-%m-%d %H:%M:%S")

        return bdt_time_str
