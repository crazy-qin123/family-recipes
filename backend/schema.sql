BEGIN;

CREATE TABLE IF NOT EXISTS public.family_recipes (
    id text PRIMARY KEY CHECK (length(id) BETWEEN 1 AND 120),
    data jsonb NOT NULL CHECK (jsonb_typeof(data) = 'object'),
    version integer NOT NULL DEFAULT 1 CHECK (version > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.family_shopping_items (
    id text PRIMARY KEY CHECK (length(id) BETWEEN 1 AND 120),
    name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 120),
    amount text NOT NULL DEFAULT '未注明' CHECK (length(amount) <= 120),
    done boolean NOT NULL DEFAULT false,
    sources jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(sources) = 'array'),
    version integer NOT NULL DEFAULT 1 CHECK (version > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.family_recipes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.family_shopping_items ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.family_recipes, public.family_shopping_items FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.family_recipes, public.family_shopping_items TO service_role;

COMMIT;

SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('family_recipes', 'family_shopping_items')
ORDER BY tablename;
