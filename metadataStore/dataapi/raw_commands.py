__author__ = 'arkilic'
__version__ = '0.0.2'
import getpass
import datetime
import re

from mongoengine.errors import OperationError

from metadataStore.database.databaseTables import Header, BeamlineConfig, Event, EventDescriptor
from metadataStore.sessionManager.databaseInit import metadataLogger


def save_header(scan_id, header_owner=getpass.getuser(), start_time=datetime.datetime.utcnow(), beamline_id=None,
                status='In Progress',custom=dict()):
    """
    Saves a run header that serves as a container for even descriptors, beamline configurations, and events.
    
    :param scan_id: Consumer specified id for a specific scan
    :type scan_id: int
    :param header_owner: Run header owner (default: debian session owner)
    :type header_owner: str
    :param start_time: Run header create time
    :type start_time: datetime object
    :param beamline_id: Beamline Id
    :type beamline_id: str
    :param status: Run header completion status( In Progress/Complete
    :type status: str
    :param custom: Additional attribute value fields that can be user defined
    :type custom: dict

    >>> save_header(scan_id=12)
    >>> save_header(scan_id=13, owner='arkilic')
    >>> save_header(scan_id=14, custom={'field1': 'value1', 'field2': 'value2'})
    >>> save_header(scan_id=15, owner='some owner', start_time=datetime.datetime(2014, 3, 4))
    >>> save_header(scan_id=15, owner='some owner', beamline_id='csx')
    >>> save_header(scan_id=15, owner='some owner', start_time=datetime.datetime(2014, 3, 4), beamline_id='csx')
    >>> save_header(scan_id=15, start_time=datetime.datetime(2014, 3, 4), custom={'att': 'value'})
    """
    try:
        header = Header(owner=header_owner, start_time=start_time,
                        end_time=start_time, beamline_id=beamline_id, scan_id=scan_id,
                        custom=custom, status=status).save(wtimeout=100,write_concern={'w': 1})
    except:
        metadataLogger.logger.warning('Header cannot be created')
        raise
    return header


def list_headers():
    """
    Return all Header instances created
    """
    try:
        headers = Header.objects.all()
    except:
        metadataLogger.logger.warning('Headers cannot be accessed')
        raise OperationError('Headers cannot be accessed')
    return headers


def get_header_object(id):
    """
    Return the Header object with given id
    
    :param id: Header _id
    :type id: pymongo.ObjectId instance
    """
    try:
        header_object = Header.objects(_id=id)
    except:
        raise
    return header_object


def get_header_id(scan_id):
    """
    Retrieve Header _id given scan_id

    :param scan_id: scan_id for a run header
    :type scan_id: int

    """
    collection = Header._get_collection()
    try:
        hdr_crsr = collection.find({'scan_id': scan_id}).limit(1)
    except:
        raise
    if hdr_crsr.count() == 0:
        raise Exception('header_id cannot be retrieved. Please validate scan_id')
    result = hdr_crsr[0]['_id']
    hdr_crsr.close()
    return result


def insert_event_descriptor(scan_id, event_type_id, event_type_name=None, type_descriptor=dict(),
                            tag=None):
    """
    Create event_descriptor entries that serve as descriptors for given events that are part of a run header
    
    :param scan_id: Consumer specified id for a specific scan
    :type scan_id: int
    :param event_type_id: Simple identifier for a given event type. Refer to api documentation for specific event types
    :type event_type_id: int
    :param event_type_name: Name information for a given event
    :type event_type_name: str
    :param type_descriptor: Additional user/data collection define attribute-value pairs
    :type type_descriptor: dict
    :param tag: Provides information regarding nature of event
    :type tag: str

    >>> insert_event_descriptor(event_descriptor_id=134, header_id=1345, event_type_id=0, event_type_name='scan')
    >>> insert_event_descriptor(event_descriptor_id=134, header_id=1345, event_type_id=0, event_type_name='scan',
    ... type_descriptor={'custom_field': 'value', 'custom_field2': 'value2'})
    >>> insert_event_descriptor(event_descriptor_id=134, header_id=1345, event_type_id=0, event_type_name='scan',
    ... type_descriptor={'custom_field': 'value', 'custom_field2': 'value2'}, tag='analysis')
    """
    #if get_event_descriptor_object(event_descriptor_id):
    #    raise ValueError('EventDescriptor with given event_descriptor_id exists')
    #else:
    header_id = get_header_id(scan_id)
    try:
        event_descriptor = EventDescriptor(header_id=header_id, event_type_id=event_type_id,
                                           event_type_name=event_type_name, type_descriptor=type_descriptor,
                                           tag=tag).save(wtimeout=100, write_concern={'w': 1})
    except:
        metadataLogger.logger.warning('EventDescriptor cannot be created')
        raise
    return event_descriptor


def get_event_descriptor_hid_edid(name, s_id):
    """
    Returns EventDescriptor instance given _id

    :param id: Unique identifier for EventDescriptor instance (refers to _id in mongodb schema)
    :type id: int
    :returns: header_id and event_descriptor_id

    """
    header_id = get_header_id(s_id)
    try:
        event_descriptor_coll = EventDescriptor._get_collection()
        result = event_descriptor_coll.find({'event_type_name': name, 'header_id': header_id}).limit(1)
    except:
        raise
    res = result[0]
    return res['header_id'], res['_id']


def list_event_descriptors():
    """
    Returns all EventDescriptor instances saved into the database
    """
    try:
        event_descriptors = EventDescriptor.objects.all()
    except:
        metadataLogger.logger.warning('EventDescriptors can not be retrieved')
        raise
    return event_descriptors


def insert_event(scan_id, descriptor_name, description=None, owner=getpass.getuser(), seq_no=None,
                 data=dict()):
    """
    Create event entries that record experimental data 
    
    :param descriptor_name: EventDescriptor name that contains info regarding set of events to be saved
    :type descriptor_name: str
    :param description: User generated optional string to be used as descriptors
    :type description: str
    :param owner: Event owner (default: debian session owner)
    :type owner: str
    :param seq_no: specifies the event's place in data sequence within a the event descriptor set
    :type seq_no: int
    :param data: Data Collection routine defined name-value 
    :type data: dict
    :Raises: TypeError, OperationError, ConnectionFailure
    :returns: Event object
    """
    header_id, descriptor_id = get_event_descriptor_hid_edid(descriptor_name, scan_id)
    try:
        event = Event(event_descriptor_id=descriptor_id, header_id=header_id, description=description,
                      owner=owner, seq_no=seq_no, data=data).save(wtimeout=100, write_concern={'w': 1})
    except:
        metadataLogger.logger.warning('Event cannot be recorded')
        raise
    return event


def save_beamline_config(beamline_cfg_id, header_id, config_params={}):
    """
    Save beamline configuration
    """
    if get_header_object(header_id):
        beamline_cfg = BeamlineConfig(_id=beamline_cfg_id, header_id=header_id, config_params=config_params)
        try:
            beamline_cfg.save(wtimeout=100, write_concern={'w': 1})
        except:
            metadataLogger.logger.warning('Beamline config cannot be saved')
            raise OperationError('Beamline config cannot be saved')
    else:
        raise ValueError('Header with given header_id cannot be located')
    return beamline_cfg


def update_header_end_time(header_id, end_time):
    """
    Updates header end_time to current timestamp given end_time and header_id. See insert_event
    """
    coll = Header._get_collection()
    try:
        result = coll.find({'_id': header_id})
    except:
        raise
    original_entry = list()
    for entry in result:
        original_entry.append(entry)
    original_entry[0]['end_time'] =  end_time
    try:
        coll.update({'_id': header_id}, original_entry[0] ,upsert=False)
    except:
        metadataLogger.logger.warning('Header end_time cannot be updated')
        raise


def update_header_status(header_id, status):
    """
    Updates run header status given header_id and status
    """
    coll = Header._get_collection()
    try:
        result = coll.find({'_id': header_id})
    except:
        raise
    original_entry = list()
    for entry in result:
        original_entry.append(entry)
    original_entry[0]['status'] =  status
    try:
        coll.update({'_id': header_id}, original_entry[0] ,upsert=False)
    except:
        metadataLogger.logger.warning('Header end_time cannot be updated')
        raise


def find(header_id=None, scan_id=None, owner=None, start_time=None, beamline_id=None, end_time=None, data=False,
         **kwargs):
    """
    Find by event_id, beamline_config_id, header_id. As of MongoEngine 0.8 the querysets utilise a local cache.
    So iterating it multiple times will only cause a single query.
    If this is not the desired behavour you can call no_cache (version 0.8.3+) to return a non-caching queryset.
     Usage:
     If contents=False, only run_header information is returned
        contents=True will return beamline_config and events related to given run_header(s)
     >>> find(header_id='last')
     >>> find(header_id='last', contents=True)
     >>> find(header_id=130, contents=True)
     >>> find(header_id=[130,123,145,247,...])
     >>> find(header_id={'start': 129, 'end': 141})
     >>> find(start_time=date.datetime(2014, 6, 13, 17, 51, 21, 987000)))
     >>> find(start_time=date.datetime(2014, 6, 13, 17, 51, 21, 987000)))
     >>> find(start_time={'start': datetime.datetime(2014, 6, 13, 17, 51, 21, 987000),
                      ... 'end': datetime.datetime(2014, 6, 13, 17, 51, 21, 987000)})
      >>> find(event_time=datetime.datetime(2014, 6, 13, 17, 51, 21, 987000)
      >>> find(event_time={'start': datetime.datetime(2014, 6, 13, 17, 51, 21, 987000})
    """
    supported_wildcard = ['*', '.', '?', '/', '^']
    query_dict = dict()
    try:
        coll = Header._get_collection()
    except:
        metadataLogger.logger.warning('Collection Header cannot be accessed')
        raise
    if scan_id is 'current':
        header_cursor = coll.find().sort([('end_time', -1)]).limit(1)
        header = header_cursor[0]
        event_desc = find_event_descriptor(header['_id'])
        i = 0
        for e_d in event_desc:
            header['event_descriptor_' + str(i)] = e_d
            events = find_event(event_descriptor_id=e_d['_id'])
            if data is True:
                header['event_descriptor_' + str(i)]['events'] = __decode_cursor(events)
                i += 1
            else:
                i += 1
    elif scan_id is 'last':
        header_cursor = coll.find().sort([('end_time', -1)]).limit(5)
        header = header_cursor[1]
        event_desc = find_event_descriptor(header['_id'])
        i = 0
        for e_d in event_desc:
            header['event_descriptor_' + str(i)] = e_d
            events = find_event(event_descriptor_id=e_d['_id'])
            if data is True:
                header['event_descriptor_' + str(i)]['events'] = __decode_cursor(events)
                i += 1
            else:
                i += 1
    else:
        if header_id is not None:
            query_dict['_id'] = header_id
        if owner is not None:
            for entry in supported_wildcard:
                    if entry in owner:
                        query_dict['owner'] = {'$regex': re.compile(owner, re.IGNORECASE)}
                        break
                    else:
                        query_dict['owner'] = owner
        if scan_id is not None:
            query_dict['scan_id'] = scan_id
        if beamline_id is not None:
            query_dict['beamline_id'] = beamline_id
        if start_time is not None:
                if isinstance(start_time, list):
                    for time_entry in start_time:
                        __validate_time([time_entry])
                    query_dict['start_time'] = {'$in': start_time}
                elif isinstance(start_time, dict):
                    __validate_time([start_time['start'],start_time['end']])
                    query_dict['start_time'] = {'$gte': start_time['start'], '$lt': start_time['end']}
                else:
                    if __validate_time([start_time]):
                        query_dict['start_time'] = {'$gte': start_time,
                                                    '$lt': datetime.datetime.utcnow()}
        if end_time is not None:
                if isinstance(end_time, list):
                    for time_entry in end_time:
                        __validate_time([time_entry])
                    query_dict['end_time'] = {'$in': end_time}
                elif isinstance(end_time, dict):
                    query_dict['end_time'] = {'$gte': end_time['start'], '$lt': end_time['end']}
                else:
                    query_dict['end_time'] = {'$gte': end_time,
                                              '$lt': datetime.datetime.utcnow()}
        header = __decode_hdr_cursor(find_header(query_dict))
        #TODO: For each header within the returned results, add event_desc field
        hdr_keys = header.keys()
        for key in hdr_keys:
            event_desc = find_event_descriptor(header[key]['_id'])
            i = 0
            for e_d in event_desc:
                header[key]['event_descriptor_' + str(i)] = e_d
                if data is True:
                    events = find_event(event_descriptor_id=e_d['_id'])
                    header[key]['event_descriptor_' + str(i)]['events'] = __decode_cursor(events)
                    i += 1
                else:
                    i += 1
    return header


def __validate_time(time_entry_list):
    for entry in time_entry_list:
        if isinstance(entry, datetime.datetime):
            flag = True
        else:
            raise TypeError('Date must be datetime object')
    return flag


def __decode_hdr_cursor(cursor_object):
    headers = dict()
    for temp_dict in cursor_object:
        headers['header_' + str(temp_dict['_id'])] = temp_dict
    return headers


def __decode_e_d_cursor(cursor_object):
    event_descriptors = dict()
    for temp_dict in cursor_object:
        event_descriptors['event_descriptor_' + str(temp_dict['_id'])] = temp_dict
    return event_descriptors


def __decode_cursor(cursor_object):
    events = dict()
    i = 0
    for temp_dict in cursor_object:
        events['event_' + str(i)] = temp_dict
        i += 1
    return events


def find_header(query_dict):
    collection = Header._get_collection()
    return collection.find(query_dict)


def find_event(event_descriptor_id, event_query_dict={}):
    event_query_dict['event_descriptor_id'] = event_descriptor_id
    collection = Event._get_collection()
    return collection.find(event_query_dict)


def find_event_descriptor(header_id, event_query_dict={}):
    event_query_dict['header_id'] = header_id
    collection = EventDescriptor._get_collection()
    return collection.find(event_query_dict)


def find_beamline_config(header_id, beamline_cfg_query_dict={}):
    beamline_cfg_query_dict['header_id'] = header_id
    collection = BeamlineConfig._get_collection()
    return collection.find(beamline_cfg_query_dict)
