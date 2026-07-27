from datetime import datetime, timedelta, timezone
class SimpleScheduler:
    """Agendador substituível: again=10min, hard=1d, good=intervalo*2, easy=intervalo*3."""
    def schedule(self, rating:str, interval_days:int=1):
        now=datetime.now(timezone.utc); interval=max(1,interval_days)
        if rating=="again": return now+timedelta(minutes=10), interval
        if rating=="hard": return now+timedelta(days=1), 1
        if rating=="good": return now+timedelta(days=interval*2), interval*2
        if rating=="easy": return now+timedelta(days=interval*3), interval*3
        if rating in {"suspend","mastered"}: return now, interval
        raise ValueError("Avaliação inválida")
