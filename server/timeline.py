"""Leitura conjunta, paginada, do histórico preservado nos formatos originais."""
import json


def history(conn, user, offset, limit):
    student = user["role"] == "student"
    owner = "p.student=:user" if student else "p.trainer=:user AND EXISTS (SELECT 1 FROM trainer_students t WHERE t.student_id=p.student AND t.trainer_id=:user)"
    legacy = "w.student_id=:user" if student else "EXISTS (SELECT 1 FROM trainer_students t WHERE t.student_id=w.student_id AND t.trainer_id=:user)"
    rows = conn.execute(f"""
      SELECT h.*,COALESCE(n.name,u.username,h.student) AS name FROM (
        SELECT 'plano' kind,v.plan id,v.version,p.student,v.created, v.data payload
        FROM versions v JOIN plans p ON p.id=v.plan WHERE {owner}
        AND (:trainer OR (p.state IN ('released','reviewed') AND json_array_length(v.data)>0))
        UNION ALL
        SELECT 'ficha_v1',w.workout_id,w.version,w.student_id,
          (julianday(w.created_at)-2440587.5)*86400,w.exercises_json FROM workout_versions w WHERE {legacy}
        UNION ALL
        SELECT 'sessao',s.id,s.version,p.student,s.created,
          json_object('day',json(s.snapshot),'actual',json(s.actual),'state',s.state)
        FROM training_sessions s JOIN plans p ON p.id=s.plan WHERE {owner}
      ) h LEFT JOIN users u ON u.user_id=h.student LEFT JOIN mobile_names n ON n.user_id=h.student
      ORDER BY h.created DESC,h.kind,h.id,h.version DESC LIMIT :limit OFFSET :offset
    """, {"user":user["id"],"trainer":not student,"limit":limit,"offset":offset})
    return [dict(row) | {"payload":json.loads(row["payload"])} for row in rows]
