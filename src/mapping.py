#from pyrundeck import RundeckApiClient
from rundeck.client import Rundeck
try:
    import configparser
except:
    from six.moves import configparser

from lxml import objectify
import codecs

def get_scheduling(job_xml):
    try:
        return 'no-scheduled' if not job_xml.job.find('schedule') else ';'.join([ str(sch.attrib) for sch in job_xml.job.schedule.getchildren()])
    except Exception as e:
        print(str(e))
        return 'No Scheduling definition found'

def get_job_definition(rundeck_client, job_id):
    response = rundeck_client.export_job(job_id)
    job_xml = objectify.fromstring(response.text)
    print("scheduleEnabled:" + str(job_xml.job.scheduleEnabled.pyval))
    print("executionEnabled:" + str(job_xml.job.executionEnabled.pyval))
    job_definition = {
        'group': job_xml.job.group.text if job_xml.job.find('group') else 'no-group',
        'executionEnabled': job_xml.job.executionEnabled.pyval,
        'scheduleEnabled': job_xml.job.scheduleEnabled.pyval,
        'schedule': get_scheduling(job_xml),
        'steps_strategy': job_xml.job.sequence.get('strategy'),
        'nodefilter': job_xml.job.nodefilters.filter.text.strip() if job_xml.job.find('nodefilters') else 'no-filter'
    }
    if job_xml.job.sequence.countchildren() > 0:
        job_definition['steps'] = [ get_job_step_info(xml_step) for xml_step in job_xml.job.sequence.getchildren() ]
    else:
        job_definition['steps'] = []
    return job_definition

def get_job_step_info(xml_step):
    try:
        xml_step_definition = xml_step.getchildren()
        #if len(xml_step_definition)
        has_description = xml_step.find('description')
        if xml_step_definition[1 if has_description else 0].tag == "jobref":
            return {
                'description': xml_step.description.text if has_description else 'no-description',
                'type': 'jobref',
                'target': xml_step.jobref.get('name'),
                'group':  xml_step.jobref.get('group') ,
                'arg':    xml_step.arg.text if xml_step.find('args') else 'no-arg'
            }
        elif xml_step_definition[1 if has_description else 0].tag == "script":
            return {
                'description': xml_step.description.text,
                'type': 'script',
                'target': xml_step.script.text,
                'args': xml_step.scriptargs.text if xml_step.find('scriptargs') else 'no-args'
            }
        else:
            raise ValueError('Not supported type step %s' % xml_step_definition[1].tag)
    except Exception as e:
        print str(e)
        return {}

def get_information_jobs(jobs, rundeck_client):
    return [ (job['project'], job['group'], job['name'], get_job_definition(rundeck_client, job['id'])) for job in jobs]

def save(file_path, data_dict):
    with codecs.open(file, "w", "utf-8") as f:
        for child in data_dict:
            f.write(str(child) + '\n')


def mapping():
    config = configparser.ConfigParser()
    config.read('../conf/rundeck_api.conf')

    api_token = config['api']['token']
    api_host  = config['api']['base_url']
    api_version = config['api']['api_version']
    rundeck = Rundeck(api_host, api_token = api_token, version = api_version)

    projects = rundeck.list_projects()
    #projects_jobs = [ (project['name'], rundeck.list_jobs(project['name'])) for project in projects ]
    projects_jobs = [ rundeck.list_jobs(project['name']) for project in projects ]
    information_jobs = [ get_information_jobs(jobs, rundeck) for jobs in projects_jobs ]

    for info_job in information_jobs:
        save("/home/alfonso/tmp/output"+ info_job[0]+".txt", info_job)

mapping()
