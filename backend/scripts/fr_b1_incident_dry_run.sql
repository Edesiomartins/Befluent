-- PostgreSQL only. Read-only incident trace: 2bbf6b59c0b5b.
-- Run in the existing production database console. No application deployment required.
-- Requires the deployed schema including users.native_language (migration 0016).
-- No names, emails, credentials, student answers or complete content JSON are returned.
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '2s';

WITH needles(value) AS (
    VALUES ('Logical Structure for Opinion & Justification in French'),
           ('Logic: In French'), ('we create a chain'), ('Connectors have fixed roles')
), candidate AS (
    SELECT 'content_units'::text AS record_type, cu.id::text AS id,
           cu.title, lg.code AS language_code, cu.cefr_level,
           cu.payload_json::jsonb AS payload,
           NULL::text AS user_ref, NULL::text AS current_user_native_language,
           cu.validation_status AS status, cu.is_active,
           jsonb_build_object('source_id', cu.source_id, 'origin_type', cu.origin_type,
                              'source_type', cs.source_type) AS stored_provenance,
           COALESCE((SELECT jsonb_agg(DISTINCT lc.lesson_id) FROM lesson_content_usages lc
                     WHERE lc.content_unit_id = cu.id), '[]'::jsonb) AS related_records,
           '[]'::jsonb AS curriculum_references
    FROM content_units cu
    LEFT JOIN languages lg ON lg.id = cu.language_id
    LEFT JOIN content_sources cs ON cs.id = cu.source_id
    UNION ALL
    SELECT 'lessons', le.id::text, le.title, lg.code,
           COALESCE(le.content_json::jsonb->>'content_level', le.content_json::jsonb->>'level'),
           le.content_json::jsonb, md5(ul.user_id::text), us.native_language,
           le.status, NULL::boolean,
           jsonb_build_object('objective', left(le.objective, 1500), 'created_at', le.created_at),
           COALESCE((SELECT jsonb_agg(jsonb_build_object(
               'content_unit_id', cu.id, 'source_id', cu.source_id, 'stored_title', cu.title,
               'origin_type', cu.origin_type, 'validation_status', cu.validation_status,
               'is_active', cu.is_active, 'payload_title', cu.payload_json::jsonb->>'title',
               'provider', cu.payload_json::jsonb->>'provider'))
               FROM lesson_content_usages lc JOIN content_units cu ON cu.id = lc.content_unit_id
               WHERE lc.lesson_id = le.id), '[]'::jsonb),
           COALESCE((SELECT jsonb_agg(jsonb_build_object('id', cb.id, 'day_id', cb.day_id,
                                                        'status', cb.status, 'cefr_level', cb.cefr_level,
                                                        'skill', cb.skill, 'topic', cb.topic))
                     FROM curriculum_blocks cb WHERE cb.lesson_ref = le.id), '[]'::jsonb)
    FROM lessons le
    JOIN user_languages ul ON ul.id = le.user_language_id
    LEFT JOIN languages lg ON lg.id = ul.language_id
    LEFT JOIN users us ON us.id = ul.user_id
    UNION ALL
    SELECT 'ai_response_cache', ca.id::text, ca.response_json::jsonb->>'title',
           ca.language_code, ca.level, ca.response_json::jsonb,
           NULL::text, NULL::text, NULL::text, NULL::boolean,
           jsonb_build_object('provider', ca.provider, 'model', ca.model,
                              'prompt_version', ca.prompt_version, 'capability', ca.capability,
                              'hit_count', ca.hit_count),
           '[]'::jsonb, '[]'::jsonb
    FROM ai_response_cache ca
), matches AS (
    SELECT * FROM candidate c
    WHERE EXISTS (SELECT 1 FROM needles n
                  WHERE c.payload::text ILIKE '%' || n.value || '%'
                     OR c.title ILIKE '%' || n.value || '%')
), output AS (
    SELECT record_type, id, title AS stored_title, language_code, cefr_level,
           user_ref, current_user_native_language, status, is_active,
           payload->>'native_language' AS payload_native_language,
           COALESCE(payload->>'target_language', payload->>'language_code') AS payload_target_language,
           jsonb_build_object('guaranteed', payload->'thread'->'guaranteed',
                              'sources', payload->'thread'->'sources') AS thread_metadata,
           (SELECT COALESCE(jsonb_object_agg(k.key, left(k.value::text, 1500)), '{}'::jsonb)
            FROM jsonb_each(CASE WHEN jsonb_typeof(payload) = 'object' THEN payload ELSE '{}'::jsonb END) k
            WHERE k.key IN ('title','subtitle','objective','explanation','logic_title',
                            'logic_title_native','explanation_native','support_language')) AS learner_fields,
           jsonb_build_object('provider', payload->>'provider', 'content_origin', payload->>'content_origin',
                              'model', payload->>'model', 'source_id', payload->>'source_id',
                              'template_id', payload->>'template_id', 'prompt_version', payload->>'prompt_version') AS payload_provenance,
           stored_provenance, related_records, curriculum_references,
           (SELECT COALESCE(jsonb_agg(k.key), '[]'::jsonb)
            FROM jsonb_each(CASE WHEN jsonb_typeof(payload) = 'object' THEN payload ELSE '{}'::jsonb END) k
            WHERE EXISTS (SELECT 1 FROM needles n WHERE k.value::text ILIKE '%' || n.value || '%')) AS contaminated_top_level_fields,
           EXISTS (SELECT 1 FROM needles n WHERE title ILIKE '%' || n.value || '%') AS stored_title_matches,
           count(*) OVER (PARTITION BY record_type) AS matched_count_in_table,
           (SELECT count(DISTINCT user_ref) FROM matches WHERE record_type = 'lessons') AS matched_users_count,
           row_number() OVER (PARTITION BY record_type ORDER BY id) AS row_in_table
    FROM matches
)
SELECT * FROM output WHERE row_in_table <= 200 ORDER BY record_type, id;
-- Zero rows means no literal matches, not proof that all content is language-valid.
-- matched_count_in_table > 200 means the output was truncated for that table.
ROLLBACK;
