# -*- encoding: utf-8 -*-

import fnmatch

from util.maven import *

LOG_STEP = "  "


def exclusion_match(exclusion_pattern, artifact: MavenArtifact):
    for k, v in exclusion_pattern.items():
        if k == "groupId":
            if not fnmatch.fnmatch(artifact.group_id, v):
                return False
        elif k == "version":
            if not fnmatch.fnmatch(artifact.version, v):
                return False
    return True


def exclusion_contains(exclusion_list, artifact: MavenArtifact):
    return any(exclusion_match(x, artifact) for x in exclusion_list)


class MavenTargetContext:
    def __init__(self, context: MavenContext, m2_home: MavenM2, root_artifacts, solution_artifacts=None):
        self.m2_home = m2_home
        self.context = context
        self.dep_configs = {}

        root_map = {}
        for artifact in root_artifacts:
            root_map[artifact.maven_key()] = artifact
        self.root_map = root_map

        solution_map = {}
        for artifact in solution_artifacts or []:
            solution_map[artifact.maven_key()] = artifact
        solution_map.update(root_map)
        self.solution_map = solution_map
        pass

    def generate_dep_configs(self, artifacts):
        deps_configs = {}

        for artifact in artifacts:
            self.generate_dep_config_impl(0, "+- ", artifact, deps_configs)

        for k, config in deps_configs.items():
            deps_list = []
            config["deps_info"] = deps_list
            for dep_item in config["deps_list"]:
                dep_artifact = MavenArtifact.parse_maven_dep(dep_item)
                assert (dep_artifact.maven_key() in deps_configs)
                dep_config = deps_configs[dep_artifact.maven_key()]
                dep_artifact = MavenArtifact(dep_config["groupId"], dep_config["artifactId"], dep_config["version"])
                deps_list.append(str(dep_artifact))
                pass

        return deps_configs

    def check_depend_conflict(self, step, log_prefix, artifact: MavenArtifact, deps_configs):
        maven_key = artifact.maven_key()
        if maven_key not in deps_configs:
            return False

        last_config = deps_configs[maven_key]
        last_artifact = MavenArtifact(last_config["groupId"], last_config["artifactId"], last_config["version"])
        if last_artifact == artifact:
            # 版本相同
            print("%s%s" % (log_prefix, artifact))
            return True

        if last_config["step"] <= step:
            # 前面的版本层次更低
            print("%s%s - omitted for conflict" % (log_prefix, artifact))
            return True

        # 现在的版本层次更低
        return False

    def generate_dep_config_impl(self, step, log_prefix, artifact: MavenArtifact, deps_configs, exclusion=None):
        maven_key = artifact.maven_key()
        if self.check_depend_conflict(step, log_prefix, artifact, deps_configs):
            return True

        print("%s%s" % (log_prefix, artifact))
        maven_pom = self.context.maven_pom(artifact, force=True)
        pom_config = maven_pom.pom_config["project"]
        config = {
            "groupId": artifact.group_id,
            "artifactId": artifact.artifact_id,
            "version": artifact.version,
            "packaging": pom_config.get("packaging", "jar"),
            "step": step,
            "deps_list": [],
        }
        deps_config = config["deps_list"]
        deps_configs[maven_key] = config

        if exclusion is None:
            exclusion = []

        dep_list = maven_pom.get_depends()
        for dep_item in dep_list:
            src_dep_artifact = MavenArtifact(dep_item["groupId"], dep_item["artifactId"], dep_item["version"])
            if src_dep_artifact == artifact:
                continue
            deps_config.append(str(src_dep_artifact))
            pass

        dep_count = len(dep_list)
        for i, dep_item in enumerate(dep_list):
            dep_log_prefix = "|  " + log_prefix.replace("\\", "+")
            if i == dep_count - 1:
                dep_log_prefix = dep_log_prefix.replace("+", "\\")
                pass
            src_dep_artifact = MavenArtifact(dep_item["groupId"], dep_item["artifactId"], dep_item["version"])
            if exclusion_contains(exclusion, src_dep_artifact):
                print("%s%s - omitted for exclusion" % (dep_log_prefix, src_dep_artifact))
                continue

            dep_exclusion = list(exclusion)
            dep_exclusion.extend(MavenPomConfig(dep_item).get_list("exclusions.exclusion"))
            self.generate_dep_config_impl(step + 1, dep_log_prefix, src_dep_artifact, deps_configs, dep_exclusion)
            pass
        pass

# def generate_target(m2_home: MavenM2, context: MavenContext, root_artifact: MavenArtifact, output_path, ):
#     target_context = MavenTargetContext(context, m2_home, root_artifact)
#     pass
