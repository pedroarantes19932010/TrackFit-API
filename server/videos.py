"""Curadoria de vídeos por treinador."""
from fastapi import Depends
from trackfit_api.catalog_routes import CATALOG, ExerciseVideo, get_exercise

SCHEMA = """
CREATE TABLE IF NOT EXISTS catalog_videos(
 trainer TEXT NOT NULL, exercise TEXT NOT NULL, youtube_id TEXT NOT NULL,
 kind TEXT NOT NULL, creator_name TEXT NOT NULL, PRIMARY KEY(trainer,exercise,youtube_id));
"""


def install(app, db, auth, trainer):
    @app.get("/catalog")
    def catalog(user=Depends(auth)):
        entries = {e.exercise_id: e.model_dump() for e in CATALOG}
        with db() as conn:
            rows = conn.execute("SELECT * FROM catalog_videos WHERE trainer=? ORDER BY rowid",
                                (user["id"] if user["role"] == "trainer" else user["trainer"],))
            for row in rows:
                entries[row["exercise"]]["videos"].append({key: row[key] for key in ("youtube_id","creator_name","kind")})
        return list(entries.values())

    @app.post("/catalog/{exercise}/videos")
    def save(exercise: str, video: ExerciseVideo, user=Depends(trainer)):
        get_exercise(exercise)
        with db(True) as conn:
            conn.execute("""INSERT INTO catalog_videos VALUES(?,?,?,?,?)
                ON CONFLICT(trainer,exercise,youtube_id) DO UPDATE SET kind=excluded.kind,creator_name=excluded.creator_name""",
                (user["id"],exercise,video.youtube_id,video.kind,video.creator_name))
        return {"ok": True}

    @app.post("/catalog/{exercise}/videos/{video_id}/remove")
    def remove(exercise: str, video_id: str, user=Depends(trainer)):
        get_exercise(exercise)
        with db(True) as conn:
            conn.execute("DELETE FROM catalog_videos WHERE trainer=? AND exercise=? AND youtube_id=?",
                         (user["id"],exercise,video_id))
        return {"ok": True}
