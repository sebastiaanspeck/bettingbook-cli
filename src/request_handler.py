from api_football_handler import ApiFootballHandler
from sportmonks_handler import SportmonksHandler


def RequestHandler(params, league_data, writer, config_handler):
    """Return the appropriate backend handler based on config [auth] backend."""
    try:
        backend = config_handler.get("auth", "backend")
    except Exception:
        backend = "api-football"

    if backend == "sportmonks":
        return SportmonksHandler(params, league_data, writer, config_handler)
    return ApiFootballHandler(params, league_data, writer, config_handler)
