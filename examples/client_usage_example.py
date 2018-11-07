""" Examples of using the client to call the web API.

"""
import getpass

from anonapi.client import WebAPIClient, APIClientAPIException


def print_to_console(msg):
    """Separate function to get some control over formatting
    """
    print("* " + msg)


def example_run():
    """ Do several example things with the anonymization server web API

    Notes
    -----
    This example talks to the 'sandbox' API server, which does not actually perform any anonymization jobs given to it.
    Instead it just stores them.

    For a full overview of API functions and parameters, load the API hostname without any parameters in your browser,
    or use function client.WebAPIClient.get_documentation()

    """

    # Create a client that will talk to the web API. The hostname is not a live anonymization server. The username is
    # the only one that is authorized on the sandbox server.
    client = WebAPIClient(
        hostname="https://umcradanonp11.umcn.nl/sandbox",
        username="z123sandbox",
        token="token",
    )
    print_to_console(f"Using client: {client}")

    # Get some information on first few jobs
    jobs_info = client.get("get_jobs")
    print_to_console(f"found {len(jobs_info)} jobs by calling {client.hostname}")

    # Get more extended information on a single job
    job_info = client.get("get_job", job_id=44778)
    print_to_console(f"Job data was {job_info}")

    # Create a job that takes data from a source on a network path, and writes the anonymized data to a destination
    # that is also a network path. Note that the network path should be accessible for the anonymization server for
    # this to work.
    anon_name = "TEST_NAME_01"
    anon_id = "01"
    source_path = r"\\umcsanfsclp01\radng_imaging\temp\test"
    destination_path = r"\\umcsanfsclp01\radng_imaging\temptest_output"
    network_job_info = client.post(
        "create_job",
        source_type="PATH",
        source_path=source_path,
        destination_type="PATH",
        project_name="Wetenschap-Algemeen",
        destination_path=destination_path,
        anonymizedpatientname=anon_name,
        anonymizedpatientid=anon_id,
        description=f"A test path job for {getpass.getuser()}",
    )
    # new_job_info response contain extended info on the new job that has just been created
    print_to_console(
        f"Succesfully created a job in {client}, job_id={network_job_info['job_id']}"
    )

    # Create a job that takes data from the IDC (formally IMPAX) directly
    anon_name = "TEST_NAME_02"
    anon_id = "02"
    sid = "123.12335.3353.36464.343435677"
    destination_path = r"\\umcsanfsclp01\radng_imaging\temptest_output"
    idc_job_info = client.post(
        "create_job",
        source_type="WADO",
        source_name="IDC_WADO",
        source_instance_id=sid,
        anonymizedpatientname=anon_name,
        anonymizedpatientid=anon_id,
        destination_type="PATH",
        project_name="Wetenschap-Algemeen",
        destination_path=destination_path,
        description=f"A test idc job for {getpass.getuser()}",
    )
    print_to_console(
        f"Succesfully created a job in {client}, job_id={idc_job_info['job_id']}"
    )

    new_job_id = idc_job_info["job_id"]

    # Check the status of your newly created job
    response = client.get("get_job", job_id=new_job_id)
    print_to_console(
        f"For the new job ({new_job_id}) that was just created, the status is {response['status']}"
    )

    # Modify the new job.
    response = client.post(
        "modify_job",
        job_id=new_job_id,
        source_path=r"\\umcsanfsclp01\radng_imaging\temp\modified\test",
    )
    print_to_console(
        f"After modification of job ({new_job_id}) source path is {response['source_path']}"
    )

    # Cancel your new job
    response = client.post("cancel_job", job_id=new_job_id)
    print_to_console(
        f"After cancelling of job ({new_job_id}) status is {response['status']}"
    )

    # To show how errors coming from the API are handled: forget to include job_id as parameter
    try:
        _ = client.post("cancel_job")
    except APIClientAPIException as e:
        msg = (
            "Errors returned by the API are returned as exceptions by the client.\n"
            "In response to a call with missing parameters this error is raised:\n"
            f"{str(e)}"
        )
        print_to_console(msg)


if __name__ == "__main__":
    example_run()
