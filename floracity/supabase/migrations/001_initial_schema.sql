-- FloraCity initial schema

-- Community plant database (grows organically via discoveries)
CREATE TABLE plants (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scientific_name text UNIQUE NOT NULL,
  common_name text,
  malay_name text,
  family text,
  description text,
  habitat text,
  wikipedia_url text,
  first_discovered_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  first_discovered_at timestamptz,
  discovery_count int NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- User profiles (created on signup via trigger)
CREATE TABLE profiles (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username text UNIQUE,
  avatar_url text,
  total_xp int NOT NULL DEFAULT 0,
  level int NOT NULL DEFAULT 1,
  pioneer_count int NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Individual discoveries (one row per user per species)
CREATE TABLE discoveries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  plant_id uuid NOT NULL REFERENCES plants(id) ON DELETE CASCADE,
  photo_url text,
  location_lat double precision,
  location_lng double precision,
  ai_confidence double precision,
  is_pioneer boolean NOT NULL DEFAULT false,
  discovered_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, plant_id)
);

-- Achievements
CREATE TABLE achievements (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  achievement_key text NOT NULL,
  unlocked_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, achievement_key)
);

-- Leaderboard view
CREATE VIEW leaderboard AS
  SELECT
    p.id,
    p.username,
    p.avatar_url,
    p.total_xp,
    p.level,
    p.pioneer_count,
    COUNT(d.id)::int AS species_count
  FROM profiles p
  LEFT JOIN discoveries d ON d.user_id = p.id
  GROUP BY p.id
  ORDER BY p.total_xp DESC;

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO profiles (id, username)
  VALUES (NEW.id, split_part(NEW.email, '@', 1));
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- RLS policies
ALTER TABLE plants ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE discoveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE achievements ENABLE ROW LEVEL SECURITY;

-- Plants: everyone can read, only authenticated can create (via edge function)
CREATE POLICY "plants_read_all" ON plants FOR SELECT USING (true);
CREATE POLICY "plants_insert_auth" ON plants FOR INSERT WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "plants_update_auth" ON plants FOR UPDATE USING (auth.role() = 'authenticated');

-- Profiles: everyone can read, users can update their own
CREATE POLICY "profiles_read_all" ON profiles FOR SELECT USING (true);
CREATE POLICY "profiles_update_own" ON profiles FOR UPDATE USING (auth.uid() = id);

-- Discoveries: everyone can read, users insert/update their own
CREATE POLICY "discoveries_read_all" ON discoveries FOR SELECT USING (true);
CREATE POLICY "discoveries_insert_own" ON discoveries FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Achievements: everyone can read
CREATE POLICY "achievements_read_all" ON achievements FOR SELECT USING (true);
CREATE POLICY "achievements_insert_own" ON achievements FOR INSERT WITH CHECK (auth.uid() = user_id);
