#from pyrundeck import RundeckApiClient
from rundeck.client import Rundeck
try:
    import configparser
except:
    from six.moves import configparser

from lxml import objectify

config = configparser.ConfigParser()
config.read('conf/rundeck_api.conf')


api_token = config['general']['token']
api_host  = config['general']['base_url']
api_version = config['general']['api_version']
rundeck = Rundeck(api_host, api_token = api_token, version = api_version)

projects = rundeck.list_projects()
projects_jobs = [ (project['name'], rundeck.list_jobs(project['name'])) for project in projects ]
projects_jobs_steps = [ (project_job[0], project_job[1], get_job_definition(project_job['id']) ) for project_job in projects_jobs ]

def get_job_definition(rundeck_client, job_id):
    response = rundeck_client.export_job(job_id)
    job_xml = objectify.fromstring(response.text)
    
    job_definition = {
        'group': job_xml.job.group.text,
        'executionEnabled': job_xml.job.executionEnabled.pyval,
        'scheduleEnabled': job_xml.job.scheduleEnabled.pyval,
        'schedule': '' if not job_xml.job.scheduleEnabled.pyval else ';'.join([ str(sch.attrib) for sch in root1_1.job.schedule.getchildren()]),
        'steps_strategy': job_xml.job.sequence.get('strategy'),
        'nodefilter': job_xml.job.nodefilters.filter.text.strip()
    }
    if job_xml.job.sequence.countchildren() > 0:
        job_definition['steps'] = [ get_job_step_info(xml_step) for xml_step in job_xml.job.sequence.getchildren() ]
    else:
        job_definition['steps'] = []
    return job_definition

def get_job_step_info(xml_step):
    xml_step_definition = xml_step.getchildren()
    if xml_step_definition[1].tag == "jobref":
        return {
            'description': xml_step_definition.description.text,
            'type': 'jobref',
            'target': xml_step_definition.jobref.get('name'),
            'group': xml_step_definition.jobref.get('group')
        }
    elif xml_step_definition[1].tag == "script":
        return {
            'description': xml_step_definition.description.text,
            'type': 'script',
            'target': xml_step_definition.script.text,
            'args': xml_step_definition.script.scriptargs.text
        }
    else:
        raise ValueError('Not supported type step %s' % xml_step_definition[1].tag)


