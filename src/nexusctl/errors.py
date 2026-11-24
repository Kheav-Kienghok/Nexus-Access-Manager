class NexusCtlError(Exception):
    pass


class UsageError(NexusCtlError):
    pass


class Cancelled(NexusCtlError):
    pass


class NexusError(NexusCtlError):
    def __init__(self, status, message, path=""):
        super().__init__("Nexus returned %s for %s: %s" % (status, path, message))
        self.status = status
        self.path = path
        self.message = message


class ProjectMissing(NexusCtlError):
    def __init__(self, project):
        super().__init__("project %s does not exist" % project)
        self.project = project
