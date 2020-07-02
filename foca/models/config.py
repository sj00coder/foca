"""FOCA config models."""

from copy import deepcopy
from enum import Enum
from functools import reduce
import importlib
import operator
from pathlib import Path
import os
from typing import (Any, Dict, List, Optional, Tuple, Union)

from pydantic import (BaseModel, Field, validator)  # pylint: disable=E0611
import pymongo


def validate_log_level_choices(level: int) -> int:
    """Custom validation function for `pydantic` to ensure that a valid
    logging level is configured.

    Args:
        level: Log level choice to be validated.

    Returns:
        Unmodified `level` value if validation succeeds.

    Raises:
        ValueError: Raised if validation fails.
    """
    choices = [0, 10, 20, 30, 40, 50]
    if level not in choices:
        raise ValueError("illegal log level specified")
    return level


def get_by_path(
    obj: Dict,
    key_sequence: List[str]
) -> Any:
    """Access a nested dictionary by sequence of keys.

    Args:
        obj: A (nested) dictionary.
        key_sequence: A sequence of keys, to be applied from outside to inside,
            pointing to the key (and descendants) to retrieve.

    Returns:
        Value of innermost key.
    """
    return reduce(operator.getitem, key_sequence, obj)  # type: ignore


class ExceptionLoggingEnum(Enum):
    """Supported config values for exception logging."""
    minimal = "minimal"
    none = "none"
    regular = "regular"
    oneline = "oneline"


class ValidationMethodsEnum(Enum):
    """Supported JWT validation methods."""
    public_key = "public_key"
    userinfo = "userinfo"


class ValidationChecksEnum(Enum):
    """Values indicating how many JWT validation methods are required to
    pass."""
    all = "all"
    any = "any"


class PymongoDirectionEnum(Enum):
    """Supported directions for Pymongo indexes."""
    ASCENDING = 1
    DESCENDING = -1
    GEO2D = "2d"
    GEOHAYSTACK = "geoHaystack"
    GEOSPHERE = "2dsphere"
    HASHED = "hashed"
    TEXT = "text"


class FOCABaseConfig(BaseModel):
    """FOCA Base Settings for Config"""

    class Config:
        """Configuration for `pydantic` model class."""
        extra = 'forbid'
        arbitrary_types_allowed = True


class ServerConfig(FOCABaseConfig):
    """Model for configuration parameters to set up a Flask or Connexion
    app instance.

    Args:
        host: Host at which the application is exposed.
        port: Port at which the application is exposed.
        debug: Flag to run application in debug mode. If `True`, the
            application runs in debug mode and an interactive debugger will
            be shown for unhandled exceptions. See Flask documentation for more
            details.
        environment: Variable to specify the application environment variable.
            See Flask documentation for more details.
        testing: Enable/disable testing mode. If `True`, exceptions are
            propagated rather than handled by the the app’s error handlers.
        use_reloader: Enable/disable the application reloader. If `debug=True`,
            enabling this will allow the server to reload automatically on
            code changes. See Flask documentation for more details.

    Attributes:
        host: Host at which the application is exposed.
        port: Port at which the application is exposed.
        debug: Flag to run application in debug mode. If `True`, the
            application runs in debug mode and an interactive debugger will
            be shown for unhandled exceptions. See Flask documentation for more
            details.
        environment: Variable to specify the application environment variable.
            See Flask documentation for more details.
        testing: Enable/disable testing mode. If `True`, exceptions are
            propagated rather than handled by the the app’s error handlers.
        use_reloader: Enable/disable the application reloader. If `debug=True`,
            enabling this will allow the server to reload automatically on
            code changes. See Flask documentation for more details.

    Raises:
        pydantic.ValidationError: The class was instantianted with an illegal
            data type.

    Example:
        >>> ServerConfig(
        ...     host="0.0.0.0",
        ...     port=8080,
        ...     debug=True,
        ...     environment="development",
        ...     testing=False,
        ...     use_reloader=True,
        ... )
        ServerConfig(host='0.0.0.0', port=8080, debug=True, environment='devel\
opment', testing=False, use_reloader=True)
    """
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = True
    environment: str = "development"
    testing: bool = False
    use_reloader: bool = True


class ExceptionConfig(FOCABaseConfig):
    """Model for app context JSON exceptions to be registered with a Connexion
    app.

    Args:
        required_members: List of dictionary keys indicating which JSON members
            are required for all exceptions. *Must* contain a member that
            represents the HTTP response code (cf. `status_member).
        extension_members: Either a list of additionally allowed, optional
            extension members, or a Boolean expression indicating whether
            any (`True`) or no (`False`) additional members are allowed.
        status_member: Sequence of dictionary keys indicating the member that
            represents the HTTP response code (e.g, `500`).
        public_members: Filter to restrict which exception members are to be
            included in the error response. Only members listed here, with each
            one specified as a sequence of keys, are included. Specify an empty
            list to prevent any members from being returned to the user. Set to
            `None` to disable filtering. Note that only one of `public_members`
            and `private_members` filters can be active.
        private_members: Filter to restrict which exception members are to be
            included in the error response. Members listed here, with each one
            specified as a sequence of keys, are excluded. Set to `None` to
            disable filtering. Note that only one of `public_members` and
            `private_members` filters can be active.
        exceptions: Path to dictionary containing the actual exception classes
            as keys and a dictionary of JSON members (as per `required_members`
            and `extension_members`) as values. Path should be a dot-separated
            path to the module containing the dictionary (which needs to also
            contain imports for all listed expcetions), followed by the name of
            the dictionary itself. For example, for `myapp.errors.exc_dict`,
            the dictionary `exc_dict` would be attempted to be imported from
            module `myapp.errors` (must be available in the Pythonpath). To
            ensure that all exceptions arising during the app context are
            handled, it is strongly advised to add the catch-all exception
            `Exception`. If missing, any exceptions not listed will only
            provoke an empty JSON response.
        logging: Specifies if and how exception details should be logged. One
            of:
                * `oneline`: Exception, including traceback, is logged on a
                single line.
                * `minimal`: Only the exception title and message are logged on
                a single line.
                * `regular`: The exception is logged with the entire traceback
                stack, generally on multiple lines.
                * `none`: Exception details are not logged at all.
            Note that unless `none` is specified, a JSON representation of the
            error, as defined in `exceptions`, and including _all_ members,
            unaffected by `public_members` and `private_members` filters, will
            be logged on an additional line.
        mapping: The actual referenced dictionary from `exceptions`, populated
            by FOCA.

    Attributes:
        required_members: List of dictionary keys indicating which JSON members
            are required for all exceptions. *Must* contain a member that
            represents the HTTP response code (cf. `status_member).
        extension_members: Either a list of additionally allowed, optional
            extension members, or a Boolean expression indicating whether
            any (`True`) or no (`False`) additional members are allowed.
        status_member: Sequence of dictionary keys indicating the member that
            represents the HTTP response code (e.g, `500`).
        public_members: Filter to restrict which exception members are to be
            included in the error response. Only members listed here, with each
            one specified as a sequence of keys, are included. Specify an empty
            list to prevent any members from being returned to the user. Set to
            `None` to disable filtering. Note that only one of `public_members`
            and `private_members` filters can be active.
        private_members: Filter to restrict which exception members are to be
            included in the error response. Members listed here, with each one
            specified as a sequence of keys, are excluded. Set to `None` to
            disable filtering. Note that only one of `public_members` and
            `private_members` filters can be active.
        exceptions: Path to dictionary containing the actual exception classes
            as keys and a dictionary of JSON members (as per `required_members`
            and `extension_members`) as values. Path should be a dot-separated
            path to the module containing the dictionary (which needs to also
            contain imports for all listed expcetions), followed by the name of
            the dictionary itself. For example, for `myapp.errors.exc_dict`,
            the dictionary `exc_dict` would be attempted to be imported from
            module `myapp.errors` (must be available in the Pythonpath). To
            ensure that all exceptions arising during the app context are
            handled, it is strongly advised to add the catch-all exception
            `Exception`. If missing, any exceptions not listed will only
            provoke an empty JSON response.
        logging: Specifies if and how exception details should be logged. One
            of:
                * `oneline`: Exception, including traceback, is logged on a
                single line.
                * `minimal`: Only the exception title and message are logged on
                a single line.
                * `regular`: The exception is logged with the entire traceback
                stack, generally on multiple lines.
                * `none`: Exception details are not logged at all.
            Note that unless `none` is specified, a JSON representation of the
            error, as defined in `exceptions`, and including _all_ members,
            unaffected by `public_members` and `private_members` filters, will
            be logged on an additional line.
        mapping: The actual referenced dictionary from `exceptions`, populated
            by FOCA.

    Raises:
        pydantic.ValidationError: The class was instantianted with an illegal
            data type.

    Example:
        >>> ExceptionConfig()
        ExceptionConfig(required_members=[['title'], ['status']], extension_me\
mbers=False, status_member=['status'], public_members=None, private_members=No\
ne, exceptions='foca.errors.exceptions.exceptions', logging=<ExceptionLoggingE\
num.oneline: 'oneline'>, mapping={<class 'Exception'>: {'title': 'Internal Ser\
ver Error', 'status': 500}, <class 'werkzeug.exceptions.BadRequest'>: {'title'\
: 'Bad Request', 'status': 400}, <class 'connexion.exceptions.ExtraParameterPr\
oblem'>: {'title': 'Bad Request', 'status': 400}, <class 'werkzeug.exceptions.\
Unauthorized'>: {'title': 'Unauthorized', 'status': 401}, <class 'werkzeug.exc\
eptions.Forbidden'>: {'title': 'Forbidden', 'status': 403}, <class 'werkzeug.e\
xceptions.NotFound'>: {'title': 'Not Found', 'status': 404}, <class 'werkzeug.\
exceptions.InternalServerError'>: {'title': 'Internal Server Error', 'status':\
 500}, <class 'werkzeug.exceptions.BadGateway'>: {'title': 'Bad Gateway', 'sta\
tus': 502}, <class 'werkzeug.exceptions.ServiceUnavailable'>: {'title': 'Servi\
ce Unavailable', 'status': 502}, <class 'werkzeug.exceptions.GatewayTimeout'>:\
 {'title': 'Gateway Timeout', 'status': 504}})
    """
    required_members: List[List[str]] = [["title"], ["status"]]
    extension_members: Union[bool, List[List[str]]] = False
    status_member: List[str] = ["status"]
    public_members: Optional[List[List[str]]] = None
    private_members: Optional[List[List[str]]] = None
    exceptions: str = "foca.errors.exceptions.exceptions"
    logging: ExceptionLoggingEnum = ExceptionLoggingEnum.oneline
    mapping: Optional[Dict[str, Dict[str, Any]]] = None

    # set mapping
    @validator('mapping', always=True, allow_reuse=True)
    def validate_mapping(cls, v, *, values):  # pylint: disable=E0213
        """Validate that exceptions dictionary exists and can be imported, that
        all exceptions have all required members and no additional members
        (unless specifically allowed) and replace default value for `field`
        mapping to the contents of the exceptions dictionaryy.
        """
        # Set allowed members
        limited_members = False
        if not (
            isinstance(values['extension_members'], bool) and
            values['extension_members']
        ):
            limited_members = True
        allowed_members = deepcopy(values['required_members'])
        if isinstance(values['extension_members'], list):
            allowed_members += values['extension_members']
        # Ensure that `exceptions` module can be imported
        split_module = values['exceptions'].split('.')
        exc_dict_name = split_module.pop()
        module_path = '.'.join(split_module)
        try:
            mod = importlib.import_module(module_path)
        except ModuleNotFoundError:
            raise ValueError(
                f"Module '{module_path}' referenced in field 'exceptions' "
                "could not be found."
            )
        # Ensure that `exceptions` module has attribute `exceptions`
        try:
            exc_dict = getattr(mod, exc_dict_name)
        except AttributeError:
            raise ValueError(
                f"Module '{module_path}' referenced in field 'exceptions' "
                f"does not have attribute '{exc_dict_name}'."
            )
        # Ensure that `exceptions` attribute is a dictionary
        if not isinstance(exc_dict, dict):
            raise TypeError(
                f"Attribute '{exc_dict_name}' in module '{module_path}' "
                "referenced in field 'exceptions' is not a dictionary."
            )
        # Ensure that `status_member` is `required_member`
        if not values['status_member'] in values['required_members']:
            raise ValueError(
                "Status member is not among required members."
            )
        # Ensure that public members are a subset of required and
        # allowed extension members, if any
        if limited_members and values['public_members']:
            if not all(m in allowed_members for m in values['public_members']):
                raise ValueError(
                    "Public members have more fields than are allowed by "
                    "'required_members' and 'extension_members'."
                )
        # Ensure that private members are a subset of required and
        # allowed extension members, if any
        if limited_members and values['private_members']:
            if not all(
                m in allowed_members for m in values['private_members']
            ):
                raise ValueError(
                    "Private members have more fields than are allowed by "
                    "'required_members' and 'extension_members'."
                )
        # Ensure that public and private members are compatible
        if (
                isinstance(values['public_members'], list) and
                isinstance(values['private_members'], list)
        ):
            raise ValueError(
                "Both public and private member filters are active, but at "
                "most one is allowed."
            )
        # Iterate over `exceptions` dictionary
        for key, val in exc_dict.items():
            # Ensure that values of `exceptions` dictionary are dictionaries
            if not isinstance(val, dict):
                raise TypeError(
                    f"Exception '{key}' in 'exceptions' dictionary does not "
                    "have member dictionary as its value."
                )
            # Ensure that keys of 'exceptions' dictionary are exceptions
            try:
                getattr(key, '__cause__')
            except AttributeError:
                raise TypeError(
                    f"Key '{key}' in 'exceptions' dictionary does not appear "
                    "to be an Exception."
                )
            # Ensure that status member can be cast to type `int`
            try:
                status = get_by_path(
                    obj=val,
                    key_sequence=values['status_member'],
                )
                status = int(status)
            except (KeyError, ValueError):
                raise ValueError(
                    f"Status member in exception '{key}' cannot be cast to "
                    "type integer."
                )
            # Ensure that all required members are available
            for keys in values['required_members']:
                try:
                    get_by_path(
                        obj=val,
                        key_sequence=keys,
                    )
                except (KeyError, ValueError):
                    raise ValueError(
                        f"Exception '{key}' in 'exceptions' dictionary does "
                        "not have all fields required by 'required_members'."
                    )
            # Ensure that available members are a subset of required and
            # allowed extension members, if any
            if limited_members:
                members = deepcopy(val)
                for keys in allowed_members:
                    try:
                        reduce(lambda v, k: v.pop(k), keys, members)
                    except KeyError:
                        pass
                if members:
                    raise ValueError(
                        f"Exception '{key}' in 'exceptions' dictionary has "
                        "more fields than are allowed by 'required_members' "
                        "and 'extension_members'."
                    )
        return exc_dict


class SpecConfig(FOCABaseConfig):
    """Model for configuration parameters for OpenAPI 2.x or 3.x specifications
    to be attached to a Connexion app.

    Args:
        path: Path to an OpenAPI 2.x or 3.x specification in YAML format.
        path_out: Output path for modified specification file. Ignored if specs
            are not modified. If not specified, the original file path is
            stripped of the file extension and the suffix '.modified.yaml' is
            appended.
        append: Fields to be added/modified in the root of the specification
            file. For OpenAPI 2, see https://swagger.io/specification/v2/. For
            OpenAPI 3, see https://swagger.io/specification/.
        add_operation_fields: Fields to be added/modified in the Operation
            Objects of each Path Info Object. An example use case for this is
            the addition or replacement of the `x-swagger-router-controller`
            field. For OpenAPI 2, see
            https://swagger.io/specification/v2/#operation-object. For OpenAPI
            3, see https://swagger.io/specification/#operation-object.
        connexion: Keyword arguments passed through to the `add_api()` method
            in Connexion's `connexion.apps.flask_app` module.

    Attributes:
        path: Path to an OpenAPI 2.x or 3.x specification in YAML format.
        path_out: Output path for modified specification file. Ignored if specs
            are not modified. If not specified, the original file path is
            stripped of the file extension and the suffix '.modified.yaml' is
            appended.
        append: Fields to be added/modified in the root of the specification
            file. For OpenAPI 2, see https://swagger.io/specification/v2/. For
            OpenAPI 3, see https://swagger.io/specification/.
        add_operation_fields: Fields to be added/modified in the Operation
            Objects of each Path Info Object. An example use case for this is
            the addition or replacement of the `x-swagger-router-controller`
            field. For OpenAPI 2, see
            https://swagger.io/specification/v2/#operation-object. For OpenAPI
            3, see https://swagger.io/specification/#operation-object.
        connexion: Keyword arguments passed through to the `add_api()` method
            in Connexion's `connexion.apps.flask_app` module.

    Raises:
        pydantic.ValidationError: The class was instantianted with an illegal
            data type.

    Example:
        >>> SpecConfig(
        ...     path="/path/to/specs.yaml",
        ...     path_out="/path/to/specs.modified.yaml",
        ...     append=[
        ...         {
        ...             "security": {
        ...                 "jwt": {
        ...                     "type": "apiKey",
        ...                     "name": "Authorization",
        ...                     "in": "header",
        ...                 }
        ...             }
        ...         },
        ...         {
        ...             "my_other_root_field": "some_value",
        ...         },
        ...     ],
        ...     add_operation_fields = {
        ...         "x-swagger-router-controller": "controllers.my_specs",
        ...         "x-some-other-custom-field": "some_value",
        ...     },
        ... )
        SpecConfig(path='/path/to/specs.yaml', path_out='/path/to/specs.modifi\
ed.yaml', append=[{'security': {'jwt': {'type': 'apiKey', 'name': 'Authorizati\
on', 'in': 'header'}}}, {'my_other_root_field': 'some_value'}], add_operation_\
fields={'x-swagger-router-controller': 'controllers.my_specs', 'x-some-other-c\
ustom-field': 'some_value'}, connexion=None)
    """
    path: str
    path_out: Optional[str] = None
    append: Optional[List[Dict]] = None
    add_operation_fields: Optional[Dict] = None
    connexion: Optional[Dict] = None

    # resolve relative path
    @validator('path', always=True, allow_reuse=True)
    def set_abs_path(cls, v):  # pylint: disable=E0213
        """Resolve path relative to caller's current working directory if no
        absolute path provided.
        """
        if not Path(v).is_absolute():
            return str(Path.cwd() / v)
        return v

    # set default if no output file path provided
    @validator('path_out', always=True, allow_reuse=True)
    def set_default_out_path(cls, v, *, values):  # pylint: disable=E0213
        """Set default output path for spec file if not supplied by user.
        """
        if 'path' in values and values['path'] is not None:
            if not v:
                return '.'.join([
                    os.path.splitext(values['path'])[0],
                    "modified.yaml"
                ])
            if not Path(v).is_absolute():
                return str(Path.cwd() / v)
        return v


class APIConfig(FOCABaseConfig):
    """Model for a list of configuration parameters for OpenAPI 2.x or 3.x
    specifications to be attached to a Connexion app.

    Args:
        spec: List of configuration parameters for OpenAPI 2.x or 3.x
            specifications to be attached to a Connexion app.

    Attributes:
        spec: List of configuration parameters for OpenAPI 2.x or 3.x
            specifications to be attached to a Connexion app.

    Raises:
        pydantic.ValidationError: The class was instantianted with an illegal
            data type.

    Example:
        >>> APIConfig(
        ...     specs=[SpecConfig(path='/path/to/specs.yaml')],
        ... )
        APIConfig(specs=[SpecConfig(path='/path/to/specs.yaml', path_out='/pat\
h/to/specs.modified.yaml', append=None, add_operation_fields=None, connexion=N\
one)])
    """
    specs: List[SpecConfig] = []


class AuthConfig(FOCABaseConfig):
    """Model for parameters used to configure JSON Web Token (JWT)-based
    authorization for the app.

    Args:
        required: Enable/disable JWT validation for endpoints decorated with
            the `@jwt_validation` decorator defined in `foca.security.auth`.
        add_key_to_claims: Whether to allow the application to add the identity
            provider's corresponding JSON Web Key (JWK), in PEM format, to the
            dictionary of claims when handling requests to
            `@jwt_validation`-decorated endpoints.
        allow_expired: Allow/disallow expired JWTs. If `False`, a `401`
            authorization error is raised in response to a request containing
            an expired JWT.
        audience: List of audiences that the app identifies itself with. If
            specified, JWTs that do not contain any of the specified audiences
            are rejected. If `None`, audience validation is disabled.
        claim_identity: The JWT claim used to identify the sender.
        claim_issuer: The JWT claim used to identify the issuer.
        claim_key_id: The JWT claim used to identify the JWK used when the JWT
            was issued.
        header_name: Name of the request header field at which the app is
            expecting the JWT. Cf. `--token-prefix`.
        token_prefix: Prefix that the app expects to precede the JWT, separated
            by whitespace. Together, prefix and JWT constitute the value of
            the request header field specified by `--header-name`.
        algorithms: Lists the JWT-signing algorithms supported by the app.
        validation_methods: Lists the methods to be used to validate a JWT.
            Valid choices are `userinfo` and `public_key`. In the former case,
            validation happens via an OpenID Connect-compliant identify
            provider's `/userinfo` endpoint, in the latter via the identity
            provider's JSON Web Key.
        validation_checks: Specify how many of the `validation_methods` need
            to pass before accepting a JWT. One of `any` and `all`. In the
            former case, JWT validation succeeds after the first successful
            validation check, in the latter case, JWT validation fails after
            the first unsuccessful validation check.

    Attributes:
        required: Enable/disable JWT validation for endpoints decorated with
            the `@jwt_validation` decorator defined in `foca.security.auth`.
        add_key_to_claims: Whether to allow the application to add the identity
            provider's corresponding JSON Web Key (JWK), in PEM format, to the
            dictionary of claims when handling requests to
            `@jwt_validation`-decorated endpoints.
        allow_expired: Allow/disallow expired JWTs. If `False`, a `401`
            authorization error is raised in response to a request containing
            an expired JWT.
        audience: List of audiences that the app identifies itself with. If
            specified, JWTs that do not contain any of the specified audiences
            are rejected. If `None`, audience validation is disabled.
        claim_identity: The JWT claim used to identify the sender.
        claim_issuer: The JWT claim used to identify the issuer.
        claim_key_id: The JWT claim used to identify the JWK used when the JWT
            was issued.
        header_name: Name of the request header field at which the app is
            expecting the JWT. Cf. `--token-prefix`.
        token_prefix: Prefix that the app expects to precede the JWT, separated
            by whitespace. Together, prefix and JWT constitute the value of
            the request header field specified by `--header-name`.
        algorithms: Lists the JWT-signing algorithms supported by the app.
        validation_methods: Lists the methods to be used to validate a JWT.
            Valid choices are `userinfo` and `public_key`. In the former case,
            validation happens via an OpenID Connect-compliant identify
            provider's `/userinfo` endpoint, in the latter via the identity
            provider's JSON Web Key.
        validation_checks: Specify how many of the `validation_methods` need
            to pass before accepting a JWT. One of `any` and `all`. In the
            former case, JWT validation succeeds after the first successful
            validation check, in the latter case, JWT validation fails after
            the first unsuccessful validation check.

    Raises:
        pydantic.ValidationError: The class was instantianted with an illegal
            data type.

    Example:
        >>> AuthConfig(
        ...     required=False,
        ...     add_key_to_claims=True,
        ...     allow_expired=False,
        ...     audience=None,
        ...     claim_identity="sub",
        ...     claim_issuer="iss",
        ...     claim_key_id="kid",
        ...     header_name="Authorization",
        ...     token_prefix="Bearer",
        ...     algorithms=["RS256"],
        ...     validation_methods=["userinfo", "public_key"],
        ...     validation_checks="all",
        ... )
        AuthConfig(required=False, add_key_to_claims=True, allow_expired=False\
, audience=None, claim_identity='sub', claim_issuer='iss', claim_key_id='kid',\
 header_name='Authorization', token_prefix='Bearer', algorithms=['RS256'], val\
idation_methods=[<ValidationMethodsEnum.userinfo: 'userinfo'>, <ValidationMeth\
odsEnum.public_key: 'public_key'>], validation_checks=<ValidationChecksEnum.al\
l: 'all'>)
    """
    required: bool = False
    add_key_to_claims: bool = True
    allow_expired: bool = False
    audience: Optional[List[str]] = None
    claim_identity: str = "sub"
    claim_issuer: str = "iss"
    claim_key_id: str = "kid"
    header_name: str = "Authorization"
    token_prefix: str = "Bearer"
    algorithms: List[str] = ["RS256"]
    validation_methods: List[ValidationMethodsEnum] = [
        ValidationMethodsEnum.userinfo,
        ValidationMethodsEnum.public_key,
    ]
    validation_checks: ValidationChecksEnum = ValidationChecksEnum.all


class SecurityConfig(FOCABaseConfig):
    """Model for list the Security configuration.

    Args:
        auth: Config parameters for JSON Web Token (JWT) validation.

    Attributes:
        auth: Config parameters for JSON Web Token (JWT) validation.

    Raises:
        pydantic.ValidationError: The class was instantianted with an illegal
            data type.

    Example:
        >>> SecurityConfig(
        ...     auth=AuthConfig(),
        ... )
        SecurityConfig(auth=AuthConfig(required=False, add_key_to_claims=True,\
 allow_expired=False, audience=None, claim_identity='sub', claim_issuer='iss',\
 claim_key_id='kid', header_name='Authorization', token_prefix='Bearer', algor\
ithms=['RS256'], validation_methods=[<ValidationMethodsEnum.userinfo: 'userinf\
o'>, <ValidationMethodsEnum.public_key: 'public_key'>], validation_checks=<Val\
idationChecksEnum.all: 'all'>))
    """
    auth: AuthConfig = AuthConfig()


class IndexConfig(FOCABaseConfig):
    """Model for configuring indexes for a MongoDB collection.

    Args:
        keys: A list of key-direction tuples indicating the field to be indexed
            and the sort order of that index. The sort order must be a valid
            MongoDB index specifier, one of `pymongo.ASCENDING`,
            `pymongo.DESCENDING`, `pymongo.GEO2D` etc. or their corresponding
            values `1`, `-1`, `'2d'`, respectively; cf.:
            https://api.mongodb.com/python/current/api/pymongo/collection.html
        name: Custom name to use for the index. If `None` is provided, a name
            will be generated.
        unique: Whether a uniqueness constraint shall be created on the index.
        background: Whether the index shall be created in the background.
        sparse: Whether documents that lack the indexed field shall be omitted
            from the index.

    Attributes:
        keys: A list of key-direction tuples indicating the field to be indexed
            and the sort order of that index. The sort order must be a valid
            MongoDB index specifier, one of `pymongo.ASCENDING`,
            `pymongo.DESCENDING`, `pymongo.GEO2D` etc. or their corresponding
            values `1`, `-1`, `'2d'`, respectively; cf.:
            https://api.mongodb.com/python/current/api/pymongo/collection.html
        name: Custom name to use for the index. If `None` is provided, a name
            will be generated.
        unique: Whether a uniqueness constraint shall be created on the index.
        background: Whether the index shall be created in the background.
        sparse: Whether documents that lack the indexed field shall be omitted
            from the index.

    Raises:
        pydantic.ValidationError: The class was instantianted with an illegal
            data type.

    Example:
        >>> IndexConfig(
        ...     keys=[('last_name', pymongo.DESCENDING)],
        ...     unique=True,
        ...     sparse=False,
        ... )
        IndexConfig(keys=[('last_name', -1)], name=None, unique=True, backgrou\
nd=False, sparse=False)
    """
    keys: Optional[List[Tuple[str, PymongoDirectionEnum]]] = None
    name: Optional[str] = None
    unique: Optional[bool] = False
    background: Optional[bool] = False
    sparse: Optional[bool] = False

    @validator('keys', always=True, allow_reuse=True)
    def store_enum_value(cls, v):  # pylint: disable=E0213
        """Store value of enumerator, rather than enumerator object."""
        if not v:
            return v
        else:
            new_v = []
            for item in v:
                tmp_list = list(item)
                tmp_list[1] = tmp_list[1].value
                new_v.append(tuple(tmp_list))
            return new_v


class CollectionConfig(FOCABaseConfig):
    """Model for configuring a MongoDB collection.

    Args:
        indexes: An index configuration object.
        client: Client connected to collection. Most likely populated through
            the code, not during setup.

    Attributes:
        indexes: An index configuration object.
        client: Client connected to collection. Most likely populated through
            the code, not during setup.

    Raises:
        pydantic.ValidationError: The class was instantianted with an illegal
            data type.

    Example:
        >>> CollectionConfig(
        ...     indexes=[IndexConfig(keys=[('last_name', 1)])],
        ... )
        CollectionConfig(indexes=[IndexConfig(keys=[('last_name', 1)], name=No\
ne, unique=False, background=False, sparse=False)], client=None)
    """
    indexes: Optional[List[IndexConfig]] = None
    client: Optional[pymongo.collection.Collection] = None


class DBConfig(FOCABaseConfig):
    """Model for configuring a MongoDB database.

    Args:
        collections: Mapping of collection names (keys) and configuration
            objects (values).
        client: Client connected to database. Most likely populated through the
            code, not during setup.

    Attributes:
        collections: Mapping of collection names (keys) and configuration
            objects (values).
        client: Client connected to database. Most likely populated through the
            code, not during setup.

    Raises:
        pydantic.ValidationError: The class was instantianted with an illegal
            data type.

    Example:
        >>> DBConfig(
        ...     collections={
        ...         'my_collection': CollectionConfig(
        ...             indexes=[IndexConfig(keys=[('last_name', 1)])],
        ...         ),
        ...     },
        ... )
        DBConfig(collections={'my_collection': CollectionConfig(indexes=[Index\
Config(keys=[('last_name', 1)], name=None, unique=False, background=False, spa\
rse=False)], client=None)}, client=None)
    """
    collections: Optional[Dict[str, CollectionConfig]] = None
    client: Optional[pymongo.database.Database] = None


class MongoConfig(FOCABaseConfig):
    """Model for configuring a MongoDB instance attached to a Flask or
    Connexion app.

    Args:
        host: Host at which the database is exposed.
        port: Port at which the database is exposed.
        dbs: Mapping of database names (keys) and configuration objects
            (values).

    Attributes:
        host: Host at which the database is exposed.
        port: Port at which the database is exposed.
        dbs: Mapping of database names (keys) and configuration objects
            (values).

    Raises:
        pydantic.ValidationError: The class was instantianted with an illegal
            data type.

    Example:
        >>> MongoConfig(
        ...     host="mongodb",
        ...     port=27017,
        ... )
        MongoConfig(host='mongodb', port=27017, dbs=None)
    """
    host: str = "mongodb"
    port: int = 27017
    dbs: Optional[Dict[str, DBConfig]] = None


class JobsConfig(FOCABaseConfig):
    """Model for configuring a RabbitMQ broker instance and Celery client
    and tasks to be attached to a Flask/Connexion app.

    Args:
        host: Host at which the broker is exposed.
        port: Port at which the broker is exposed.
        backend: Backend used to store background task results.
        include: List of modules to import when workers start.

    Attributes:
        host: Host at which the broker is exposed.
        port: Port at which the broker is exposed.
        backend: Backend used to store background task results.
        include: List of modules to import when workers start.

    Raises:
        pydantic.ValidationError: The class was instantianted with an illegal
            data type.

    Example:
        >>> JobsConfig(
        ...     host="rabbitmq",
        ...     port=5672,
        ...     backend='rpc://',
        ...     include=[],
        ... )
        JobsConfig(host='rabbitmq', port=5672, backend='rpc://', include=[])
    """
    host: str = "rabbitmq"
    port: int = 5672
    backend: str = 'rpc://'
    include: Optional[List[str]] = None


class LogFormatterConfig(FOCABaseConfig):
    """Model for formatter for LogConfig.

    Args:
        class: Name of logging formatter class.
        style: Determines how the format string will be merged with its data.
        format: Format string any log messages.

    Attributes:
        class: Name of logging formatter class.
        style: Determines how the format string will be merged with its data.
        format: Format string any log messages.

    Raises:
        pydantic.ValidationError: The class was instantianted with an illegal
            data type.

    Example:
        >>> LogFormatterConfig(
        ...     style="{",
        ...     format="[{asctime}: {levelname:<8}] {message} [{name}]",
        ... )
        LogFormatterConfig(class_formatter='logging.Formatter', style='{', for\
mat='[{asctime}: {levelname:<8}] {message} [{name}]')
    """
    class_formatter: str = Field(
        "logging.Formatter",
        alias="class",
    )
    style: str = "{"
    format: str = "[{asctime}: {levelname:<8}] {message} [{name}]"


class LogHandlerConfig(FOCABaseConfig):
    """Model for passing logging handler parameters to configuring app logging.

    Args:
        class: Name of logging handler class.
        level: Numeric value of logging level.
        formatter: Name of logging formatter.
        stream: Devide to which log is streamed.

    Attributes:
        class: Name of logging handler class.
        level: Numeric value of logging level.
        formatter: Name of logging formatter.
        stream: Devide to which log is streamed.

    Raises:
        pydantic.ValidationError: The class was instantianted with an illegal
            data type.

    Example:
        >>> LogHandlerConfig(
        ...     level=20,
        ...     formatter="standard",
        ...     stream="ext://sys.stderr",
        ... )
        LogHandlerConfig(class_handler='logging.StreamHandler', level=20, form\
atter='standard', stream='ext://sys.stderr')
    """
    class_handler: str = Field(
        "logging.StreamHandler",
        alias="class",
    )
    level: int = 20
    formatter: str = "standard"
    stream: str = "ext://sys.stderr"

    _validate_level = validator('level', allow_reuse=True)(
        validate_log_level_choices
    )


class LogRootConfig(FOCABaseConfig):
    """Model for root log configuration.

    Args:
        level: Numeric value of logging level.
        handlers: List of logging handlers by name.

    Attributes:
        level: Numeric value of logging level.
        handlers: List of logging handlers by name.

    Raises:
        pydantic.ValidationError: The class was instantianted with an illegal
            data type.

    Example:
        >>> LogRootConfig(
        ...     level=logging.INFO,
        ...     handlers=["console"],
        ... )
        LogRootConfig(level=20, handlers=['console'])
    """
    level: int = 10
    handlers: Optional[List[str]] = ["console"]

    _validate_level = validator('level', allow_reuse=True)(
        validate_log_level_choices
    )


class LogConfig(FOCABaseConfig):
    """Model for passing parameters for configuring app logging.

    Args:
        version: Schema version.
        disable_existing_loggers: Whether any existing non-root loggers are to
            be disabled.
        formatters: A dictionary of logging formatters, where keys represent
            formatter names and values represent the corresponding
            configuration parameters.
        handlers: A dictionary of logging handlers, where keys represent
            handler names and values represent the corresponding configuration
            parameters.
        root: Configuration of the root logger.

    Attributes:
        version: Represents current schema version.
        disable_existing_loggers: Whether any existing non-root loggers are to
            be disabled.
        formatters: A dictionary of logging formatters, where keys represent
            formatter names and values represent the corresponding
            configuration parameters.
        handlers: A dictionary of logging handlers, where keys represent
            handler names and values represent the corresponding configuration
            parameters.
        root: Configuration of the root logger.

    Raises:
        pydantic.ValidationError: The class was instantianted with an illegal
            data type.

    Example:
        >>> LogConfig(
        ...     version=1,
        ...     disable_existing_loggers=False,
        ...     formatters={
        ...         "standard": LogFormatterConfig()
        ...     },
        ...     handlers={
        ...         "console": LogHandlerConfig()
        ...     },
        ...     root=LogRootConfig()
        ... )
        LogConfig(version=1, disable_existing_loggers=False, formatters={'stan\
dard': LogFormatterConfig(class_formatter='logging.Formatter', style='{', form\
at='[{asctime}: {levelname:<8}] {message} [{name}]')}, handlers={'console': Lo\
gHandlerConfig(class_handler='logging.StreamHandler', level=20, formatter='sta\
ndard', stream='ext://sys.stderr')}, root=LogRootConfig(level=10, handlers=['c\
onsole']))
    """
    version: int = 1
    disable_existing_loggers: bool = False
    formatters: Optional[Dict[str, LogFormatterConfig]] = {
        "standard": LogFormatterConfig(),
    }
    handlers: Optional[Dict[str, LogHandlerConfig]] = {
        "console": LogHandlerConfig(),
    }
    root: Optional[LogRootConfig] = LogRootConfig()


class Config(FOCABaseConfig):
    """Model for all app configuration parameters.

    Args:
        server: Server config parameters.
        exceptions: Exception handling parameters.
        api: OpenAPI specification config parameters.
        security: Security config parameters.
        db: Database config parameters.
        jobs: Background job config parameters.
        log: Logger config parameters.

    Attributes:
        server: Server config parameters.
        exceptions: Exception handling parameters.
        api: OpenAPI specification config parameters.
        security: Security config parameters.
        db: Database config parameters.
        jobs: Background job config parameters.
        log: Logger config parameters.

    Raises:
        pydantic.ValidationError: The class was instantianted with an illegal
            data type.

    Example:
        >>> Config()
        Config(server=ServerConfig(host='0.0.0.0', port=8080, debug=True, envi\
ronment='development', testing=False, use_reloader=True), exceptions=Exception\
Config(required_members=['title', 'status'], extension_members=False, status_m\
ember='status', exceptions='foca.errors.exceptions', mapping={<class 'Exceptio\
n'>: {'title': 'An unexpected error occurred.', 'status': 500}, <class 'werkze\
ug.exceptions.InternalServerError'>: {'title': 'An unexpected error occurred.'\
, 'status': 500}, <class 'werkzeug.exceptions.BadRequest'>: {'title': 'The req\
uest is malformed.', 'status': 400}, <class 'connexion.exceptions.ExtraParamet\
erProblem'>: {'title': 'The request is malformed.', 'status': 400}, <class 'we\
rkzeug.exceptions.Forbidden'>: {'title': 'The requester is not authorized to p\
erform this action.', 'status': 403}, <class 'werkzeug.exceptions.NotFound'>: \
{'title': 'The requested resource was not found.', 'status': 404}, <class 'wer\
kzeug.exceptions.Unauthorized'>: {'title': 'The request is unauthorized.', 'st\
atus': 401}}), api=APIConfig(specs=[]), security=SecurityConfig(auth=AuthConfi\
g(required=False, add_key_to_claims=True, allow_expired=False, audience=None, \
claim_identity='sub', claim_issuer='iss', claim_key_id='kid', header_name='Aut\
horization', token_prefix='Bearer', algorithms=['RS256'], validation_methods=[\
<ValidationMethodsEnum.userinfo: 'userinfo'>, <ValidationMethodsEnum.public_ke\
y: 'public_key'>], validation_checks=<ValidationChecksEnum.all: 'all'>)), db=N\
one, jobs=None, log=LogConfig(version=1, disable_existing_loggers=False, forma\
tters={'standard': LogFormatterConfig(class_formatter='logging.Formatter', sty\
le='{', format='[{asctime}: {levelname:<8}] {message} [{name}]')}, handlers={'\
console': LogHandlerConfig(class_handler='logging.StreamHandler', level=20, fo\
rmatter='standard', stream='ext://sys.stderr')}, root=LogRootConfig(level=10, \
handlers=['console'])))
    """
    server: ServerConfig = ServerConfig()
    exceptions: ExceptionConfig = ExceptionConfig()
    api: APIConfig = APIConfig()
    security: SecurityConfig = SecurityConfig()
    db: Optional[MongoConfig] = None
    jobs: Optional[JobsConfig] = None
    log: LogConfig = LogConfig()

    class Config:
        """Configuration for `pydantic` model class."""
        extra = 'allow'