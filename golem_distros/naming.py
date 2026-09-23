RELEASES_DIRECTORY = "releases"
LATEST_KEY = f"{RELEASES_DIRECTORY}/latest.json"
CHECKSUM_SUFFIX = ".sha512"
DIGEST_LENGTH = 128
SHORT_LENGTH = 16


def image_key(distro_name: str, version: str, sha512: str) -> str:
    if len(sha512) != DIGEST_LENGTH:
        raise ValueError(f"a sha512 digest has {DIGEST_LENGTH} characters")
    return f"{distro_name}/{version}/{distro_name}-{sha512[:SHORT_LENGTH]}.qcow2"


def manifest_key(version: str) -> str:
    return f"{RELEASES_DIRECTORY}/{version}.json"


def public_url(base_url: str, key: str) -> str:
    return f"{base_url.rstrip('/')}/{key}"


def published_name(key: str) -> str:
    return key.rsplit("/", 1)[-1]


def sidecar(sha512: str, name: str) -> str:
    return f"{sha512}  {name}\n"
