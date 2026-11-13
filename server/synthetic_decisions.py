"""Modelo experimental de motivos de revisão. Só usa cenários gerados localmente."""
import itertools
import json
import math
import random
from collections import Counter, defaultdict

FIELDS=("restricao","ausente","alternativa","minutos_curtos","dificil","preferencia","nivel","dias","local")
PROB=(.12,.35,.55,.28,.20,.15)
# Parâmetros fictícios para variar o teste; não são prevalências observadas.
def scenarios(seed):
    rng=random.Random(seed)
    for flags in itertools.product((0,1),repeat=6):
        for level,days,place in itertools.product(("iniciante","intermediario"),(2,3,4),("casa","academia")):
            inputs=flags+(level,days,place)
            label=("avaliacao" if flags[0] else "equipamento" if flags[1] and not flags[2]
                   else "tempo" if flags[3] else "dificuldade" if flags[4] else "preferencia" if flags[5] else "manter")
            weight=math.prod(p if bit else 1-p for bit,p in zip(flags,PROB))
            yield inputs,label,weight,rng.random()

def run():
    cases=list(scenarios(1749))
    train=[c for c in cases if c[3]>=.25]
    holdout=[c for c in cases if c[3]<.25]
    assert not {r[0] for r in train}&{r[0] for r in holdout}
    totals=Counter()
    counts=defaultdict(Counter)
    for x,label,w,_ in train:
        totals[label]+=w
        for i,value in enumerate(x):
            counts[label,i][value]+=w
    correct=0
    confusion=defaultdict(Counter)
    for x,expected,w,_ in holdout:
        def score(label):
            return math.log(totals[label])+sum(math.log((counts[label,i][v]+.001)/(totals[label]+.001*len({r[0][i] for r in train}))) for i,v in enumerate(x))
        predicted=max(totals,key=score)
        correct+=predicted==expected
        confusion[expected][predicted]+=1
    return {"treino":len(train),"teste_separado":len(holdout),"acertos":correct,"matriz":confusion,"probabilidades_hipoteticas":dict(zip(FIELDS,PROB))}
if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,indent=2))
