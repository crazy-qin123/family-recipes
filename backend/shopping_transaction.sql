BEGIN;
CREATE TABLE IF NOT EXISTS public.family_operations (
  id text PRIMARY KEY,
  payload jsonb NOT NULL,
  result jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.family_operations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.family_operations FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON public.family_operations TO service_role;

CREATE OR REPLACE FUNCTION public.family_apply_shopping(operation_id text, changes jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path = public, pg_temp AS $$
DECLARE
  previous public.family_operations%ROWTYPE;
  change jsonb;
  affected integer;
  output jsonb;
BEGIN
  IF length(operation_id) NOT BETWEEN 1 AND 120 OR jsonb_typeof(changes) <> 'array'
     OR jsonb_array_length(changes) > 200 THEN
    RAISE EXCEPTION 'Invalid operation';
  END IF;
  PERFORM pg_advisory_xact_lock(73918462);
  SELECT * INTO previous FROM public.family_operations WHERE id = operation_id;
  IF FOUND THEN
    IF previous.payload <> changes THEN
      RAISE EXCEPTION USING ERRCODE = '23505', MESSAGE = 'Operation payload changed';
    END IF;
    RETURN previous.result;
  END IF;
  FOR change IN SELECT value FROM jsonb_array_elements(changes) LOOP
    IF (change->>'version')::integer = 0 THEN
      INSERT INTO public.family_shopping_items(id, name, amount, done, sources)
      VALUES(change->>'id', change->>'name', change->>'amount',
             (change->>'done')::boolean, change->'sources');
    ELSIF coalesce((change->>'delete')::boolean, false) THEN
      DELETE FROM public.family_shopping_items
      WHERE id = change->>'id' AND version = (change->>'version')::integer;
      GET DIAGNOSTICS affected = ROW_COUNT;
      IF affected <> 1 THEN
        RAISE EXCEPTION USING ERRCODE = '23505', MESSAGE = 'Version conflict';
      END IF;
    ELSE
      UPDATE public.family_shopping_items SET name = change->>'name',
        amount = change->>'amount', done = (change->>'done')::boolean,
        sources = change->'sources', version = version + 1, updated_at = now()
      WHERE id = change->>'id' AND version = (change->>'version')::integer;
      GET DIAGNOSTICS affected = ROW_COUNT;
      IF affected <> 1 THEN
        RAISE EXCEPTION USING ERRCODE = '23505', MESSAGE = 'Version conflict';
      END IF;
    END IF;
  END LOOP;
  output := jsonb_build_object('saved', true);
  INSERT INTO public.family_operations(id, payload, result) VALUES(operation_id, changes, output);
  RETURN output;
END;
$$;
REVOKE ALL ON FUNCTION public.family_apply_shopping(text, jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.family_apply_shopping(text, jsonb) TO service_role;
COMMIT;
