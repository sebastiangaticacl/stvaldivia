"""
Mensajes motivacionales y amigables para el sistema
"""
import random
from datetime import datetime

# Mensajes de bienvenida personalizados
WELCOME_MESSAGES = [
    "¡Hola {name}! 👋 ¡Listo para una gran jornada!",
    "¡Bienvenido {name}! 🌟 ¡Vamos a hacer que hoy sea increíble!",
    "¡Hola {name}! 💪 ¡Estamos contigo para hacer un excelente trabajo!",
    "¡Bienvenido {name}! 🚀 ¡Hoy será un día exitoso!",
    "¡Hola {name}! ⭐ ¡Gracias por ser parte del equipo!",
    "¡Bienvenido {name}! 🎯 ¡Vamos a superar todas las metas!",
    "¡Hola {name}! 💎 ¡Tu dedicación hace la diferencia!",
    "¡Bienvenido {name}! 🔥 ¡Estamos listos para brillar!",
]

# Mensajes motivacionales para el trabajo
MOTIVATIONAL_MESSAGES = [
    "¡Sigue así! 💪 Estás haciendo un excelente trabajo",
    "¡Excelente! ⭐ Cada venta cuenta",
    "¡Vamos! 🚀 Estás en el camino correcto",
    "¡Genial! 🌟 Tu esfuerzo se nota",
    "¡Perfecto! 💎 Sigue con ese ritmo",
    "¡Increíble! 🔥 Estás siendo productivo",
    "¡Bien hecho! 🎯 Mantén ese nivel",
    "¡Fantástico! ⚡ Tu dedicación es admirable",
]

# Mensajes de aliento durante el turno
ENCOURAGEMENT_MESSAGES = [
    "¡Estás haciendo un gran trabajo! 💪",
    "¡Cada venta te acerca más a la meta! 🎯",
    "¡Sigue así, vas excelente! ⭐",
    "¡Tu actitud positiva marca la diferencia! 🌟",
    "¡Estás siendo muy eficiente! 🚀",
    "¡Gracias por tu dedicación! 💎",
    "¡Vamos por más! 🔥",
    "¡Estás en tu mejor momento! ⚡",
]

# Mensajes de logro
ACHIEVEMENT_MESSAGES = {
    'first_sale': "🎉 ¡Primera venta del día! ¡Excelente comienzo!",
    'milestone_10': "🎊 ¡10 ventas completadas! ¡Sigue así!",
    'milestone_25': "🏆 ¡25 ventas! ¡Estás siendo increíble!",
    'milestone_50': "👑 ¡50 ventas! ¡Eres un campeón!",
    'milestone_100': "💎 ¡100 ventas! ¡Leyenda en acción!",
    'fast_sale': "⚡ ¡Venta rápida! ¡Excelente eficiencia!",
    'high_value': "💰 ¡Venta de alto valor! ¡Bien hecho!",
}


def get_welcome_message(name: str) -> str:
    """
    Obtiene un mensaje de bienvenida aleatorio personalizado
    
    Args:
        name: Nombre del usuario
        
    Returns:
        Mensaje de bienvenida
    """
    message = random.choice(WELCOME_MESSAGES)
    return message.format(name=name)


def get_motivational_message() -> str:
    """
    Obtiene un mensaje motivacional aleatorio
    
    Returns:
        Mensaje motivacional
    """
    return random.choice(MOTIVATIONAL_MESSAGES)


def get_encouragement_message() -> str:
    """
    Obtiene un mensaje de aliento aleatorio
    
    Returns:
        Mensaje de aliento
    """
    return random.choice(ENCOURAGEMENT_MESSAGES)


def get_achievement_message(achievement_type: str) -> str:
    """
    Obtiene un mensaje de logro específico
    
    Args:
        achievement_type: Tipo de logro
        
    Returns:
        Mensaje de logro o mensaje genérico si no existe
    """
    return ACHIEVEMENT_MESSAGES.get(achievement_type, "¡Bien hecho! 🎉")


def get_time_based_greeting() -> str:
    """
    Obtiene un saludo basado en la hora del día
    
    Returns:
        Saludo apropiado para la hora
    """
    hour = datetime.now().hour
    
    if 5 <= hour < 12:
        return "¡Buenos días! ☀️"
    elif 12 <= hour < 18:
        return "¡Buenas tardes! 🌤️"
    elif 18 <= hour < 22:
        return "¡Buenas noches! 🌙"
    else:
        return "¡Bienvenido! 🌃"


def get_daily_quote() -> str:
    """
    Obtiene una frase del día motivacional
    
    Returns:
        Frase motivacional
    """
    quotes = [
        "El éxito es la suma de pequeños esfuerzos repetidos día tras día. 💪",
        "Cada venta es una oportunidad de hacer sonreír a alguien. 😊",
        "Tu actitud positiva es contagiosa. ¡Sigue así! ⭐",
        "El trabajo en equipo hace que los sueños se hagan realidad. 🤝",
        "Cada día es una nueva oportunidad de superarte. 🚀",
        "La excelencia no es un acto, es un hábito. 💎",
        "Tu dedicación de hoy construye el éxito de mañana. 🔥",
    ]
    
    # Usar el día del año para tener una cita consistente por día
    day_of_year = datetime.now().timetuple().tm_yday
    return quotes[day_of_year % len(quotes)]







