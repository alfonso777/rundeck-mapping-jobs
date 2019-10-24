#from pyrundeck import RundeckApiClient
from rundeck.client import Rundeck
try:
    import configparser
except:
    from six.moves import configparser

from lxml import objectify
import codecs
import json

def get_job_definition(rundeck_client, job_id):
    response = rundeck_client.export_job(job_id)
    job_xml = objectify.fromstring(response.text)
    print("job %s , id: %s" % (job_xml.job.name.text, job_xml.job.id.text))
    job_definition = {
        "id": job_xml.job.id.text,
        "name": job_xml.job.name.text,
        "group": job_xml.job.group.text if job_xml.job.find('group') else 'no-group',
        "executionEnabled": job_xml.job.executionEnabled.pyval,
        "scheduleEnabled": job_xml.job.scheduleEnabled.pyval,
        "schedule": "no-schedule" if not job_xml.job.find('schedule') else ';'.join([ str(sch.attrib) for sch in job_xml.job.schedule.getchildren()]),
        "steps_strategy": job_xml.job.sequence.get('strategy'),
        "nodefilter": job_xml.job.nodefilters.filter.text.strip() if job_xml.job.find('nodefilters') else 'no-filter'
    }
    if job_xml.job.sequence.countchildren() > 0:
        job_definition["steps"] = [ get_job_step_info(xml_step) for xml_step in job_xml.job.sequence.getchildren() ]
    else:
        job_definition["steps"] = []
    return job_definition

def get_job_step_info(xml_step):
    try:
        xml_step_definition = xml_step.getchildren()
        has_description = xml_step.find('description')
        if xml_step_definition[1 if has_description else 0].tag == "jobref":
            return {
                "description": xml_step.description.text if has_description else "no-description",
                "type": "jobref",
                "group":  xml_step.jobref.get('group'),
                "target": xml_step.jobref.get('name'),
                "extra":  xml_step.arg.text if xml_step.find('args') else "no-arg"
            }
        elif xml_step_definition[1 if has_description else 0].tag == "script":
            return {
                "description": xml_step.description.text if has_description else "no-description",
                "type": "script",
                "group": "", 
                "target": xml_step.script.text,
                "extra": xml_step.scriptargs.text if xml_step.find('scriptargs') else "no-args"
            }
        elif xml_step_definition[1 if has_description else 0].tag == "step-plugin":
            return {
                "description": xml_step.description.text if has_description else "no-description",
                "type": "step-plugin",
                "group": "", 
                "target": ';'.join([ str(entry.attrib)  for entry in xml_step['step-plugin'].configuration.getchildren() ]),
                "extra": xml_step['step-plugin'].get('type')
            }
        else:
            raise ValueError('Not supported type step %s' % xml_step_definition[1].tag)
    except Exception as e:
        print str(e)
        return {}

def get_information_jobs(jobs, rundeck_client):
    return [ get_job_definition(rundeck_client, job['id']) for job in jobs]

def save(file_path, data_dict):
    with codecs.open(file_path, "w", "utf-8") as f:
        f.write(json.dumps(data_dict, sort_keys=True, indent=2))


def mapping():
    config = configparser.ConfigParser()
    config.read('../conf/rundeck_api.conf')

    api_token = config['api']['token']
    api_host  = config['api']['base_url']
    api_version = config['api']['api_version']
    rundeck = Rundeck(api_host, api_token = api_token, version = api_version)

    projects = rundeck.list_projects()
    projects_jobs = { project['name']: rundeck.list_jobs(project['name']) for project in projects }
    information_jobs = { project_name: get_information_jobs(jobs, rundeck) for project_name, jobs in projects_jobs.items() }

    for project_name, info_jobs in information_jobs.items():
        print("projeto: %s" % project_name)
        save("/home/alfonso/tmp/output-%s.txt" % project_name, info_jobs)

mapping()
