from user_agents import parse


def traducir_user_agent(ua_string: str) -> str:
    ua = parse(ua_string or "")

    navegador = ua.browser.family or "Navegador"
    version = ua.browser.version_string or ""
    sistema = ua.os.family or "Sistema"

    if ua.is_mobile:
        tipo = "Móvil"
    elif ua.is_tablet:
        tipo = "Tablet"
    else:
        tipo = "PC"

    if version:
        return f"{navegador} {version} · {sistema} ({tipo})"

    return f"{navegador} · {sistema} ({tipo})"
