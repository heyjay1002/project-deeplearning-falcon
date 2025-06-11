from datetime import datetime
from config import ObjectType, AirportZone

sample_object_data = [
    {
        'object_id': 1,
        'object_type': ObjectType.BIRD,
        'x_coord': 100.0,
        'y_coord': 200.0,
        'zone': AirportZone.RWY_A,
        'timestamp': datetime.now(),
        'risk_level': None,
        'extra_info': None
    }
]