-- Create mood_entries table for emotion diary tracking
-- This table stores daily mood entries for students

CREATE TABLE IF NOT EXISTS mood_entries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mood_value INTEGER NOT NULL CHECK (mood_value >= 20 AND mood_value <= 100),
    note TEXT,
    mood_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- One entry per user per day
    UNIQUE(user_id, mood_date)
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_mood_entries_user_id ON mood_entries(user_id);
CREATE INDEX IF NOT EXISTS idx_mood_entries_mood_date ON mood_entries(mood_date);
CREATE INDEX IF NOT EXISTS idx_mood_entries_user_date ON mood_entries(user_id, mood_date DESC);

-- Create trigger to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_mood_entries_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_mood_entries_updated_at
    BEFORE UPDATE ON mood_entries
    FOR EACH ROW
    EXECUTE FUNCTION update_mood_entries_updated_at();

-- Add comment to table
COMMENT ON TABLE mood_entries IS 'Stores daily mood/emotion diary entries for students';
COMMENT ON COLUMN mood_entries.mood_value IS 'Mood value: 20=Angry, 40=Sad, 60=Normal, 80=Happy, 100=Great';
COMMENT ON COLUMN mood_entries.mood_date IS 'Date of the mood entry (unique per user per day)';
