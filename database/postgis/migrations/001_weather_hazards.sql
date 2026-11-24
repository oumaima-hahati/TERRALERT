
BEGIN;

-- 1. HISTORICAL DAILY WEATHER

CREATE TABLE IF NOT EXISTS public.weather_daily (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    commune_code VARCHAR(254) NOT NULL
        REFERENCES public.communes(iso),

    observation_date DATE NOT NULL,
    source TEXT NOT NULL,
    source_version TEXT NOT NULL DEFAULT 'unspecified',

    rainfall_mm DOUBLE PRECISION
        CHECK (rainfall_mm >= 0),

    rainfall_3d_mm DOUBLE PRECISION
        CHECK (rainfall_3d_mm >= 0),

    rainfall_7d_mm DOUBLE PRECISION
        CHECK (rainfall_7d_mm >= 0),

    rainfall_30d_mm DOUBLE PRECISION
        CHECK (rainfall_30d_mm >= 0),

    temperature_min_c DOUBLE PRECISION,
    temperature_max_c DOUBLE PRECISION,
    temperature_mean_c DOUBLE PRECISION,

    humidity_pct DOUBLE PRECISION
        CHECK (humidity_pct BETWEEN 0 AND 100),

    wind_speed_kmh DOUBLE PRECISION
        CHECK (wind_speed_kmh >= 0),

    valid_coverage_pct DOUBLE PRECISION
        CHECK (valid_coverage_pct BETWEEN 0 AND 100),

    metadata JSONB NOT NULL DEFAULT '{}',
    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (temperature_min_c <= temperature_max_c),

    UNIQUE (
        commune_code,
        observation_date,
        source,
        source_version
    )
);


-- 2. WEATHER FORECASTS

CREATE TABLE IF NOT EXISTS public.weather_forecasts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    commune_code VARCHAR(254) NOT NULL
        REFERENCES public.communes(iso),

    source TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT 'unspecified',

    retrieved_at TIMESTAMPTZ NOT NULL,
    valid_at TIMESTAMPTZ NOT NULL,

    temperature_c DOUBLE PRECISION,

    rainfall_mm DOUBLE PRECISION
        CHECK (rainfall_mm >= 0),

    humidity_pct DOUBLE PRECISION
        CHECK (humidity_pct BETWEEN 0 AND 100),

    wind_speed_kmh DOUBLE PRECISION
        CHECK (wind_speed_kmh >= 0),

    wind_direction_deg DOUBLE PRECISION
        CHECK (wind_direction_deg BETWEEN 0 AND 360),

    grid_latitude DOUBLE PRECISION
        CHECK (grid_latitude BETWEEN -90 AND 90),

    grid_longitude DOUBLE PRECISION
        CHECK (grid_longitude BETWEEN -180 AND 180),

    metadata JSONB NOT NULL DEFAULT '{}',

    UNIQUE (
        commune_code,
        source,
        model,
        retrieved_at,
        valid_at
    )
);


-- 3. NASA FIRMS FIRE DETECTIONS

CREATE TABLE IF NOT EXISTS public.fire_detections (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    detection_uid TEXT NOT NULL UNIQUE,

    commune_code VARCHAR(254)
        REFERENCES public.communes(iso),

    detected_at TIMESTAMPTZ NOT NULL,

    source TEXT NOT NULL,
    satellite TEXT,
    instrument TEXT,
    confidence TEXT,

    frp_mw DOUBLE PRECISION
        CHECK (frp_mw >= 0),

    geom GEOMETRY(Point,4326) NOT NULL,

    metadata JSONB NOT NULL DEFAULT '{}',
    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- 4. MULTI-HAZARD MODEL RESULTS

CREATE TABLE IF NOT EXISTS public.hazard_assessments (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    commune_code VARCHAR(254) NOT NULL
        REFERENCES public.communes(iso),

    hazard_type TEXT NOT NULL CHECK (
        hazard_type IN (
            'flood',
            'wildfire',
            'heatwave',
            'coldwave'
        )
    ),

    assessment_type TEXT NOT NULL CHECK (
        assessment_type IN (
            'susceptibility',
            'historical',
            'current',
            'forecast'
        )
    ),

    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,

    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ,

    risk_score DOUBLE PRECISION
        CHECK (risk_score BETWEEN 0 AND 100),

    risk_level TEXT CHECK (
        risk_level IN (
            'very_low',
            'low',
            'moderate',
            'high',
            'very_high'
        )
    ),

    validation_status TEXT NOT NULL
        DEFAULT 'unvalidated'
        CHECK (
            validation_status IN (
                'unvalidated',
                'provisional',
                'validated'
            )
        ),

    indicators JSONB NOT NULL DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}',

    CHECK (
        valid_until IS NULL
        OR valid_until > valid_from
    ),

    UNIQUE (
        commune_code,
        hazard_type,
        assessment_type,
        model_name,
        model_version,
        generated_at,
        valid_from
    )
);


-- 5. HAZARD ALERT HISTORY

CREATE TABLE IF NOT EXISTS public.hazard_alerts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    assessment_id BIGINT NOT NULL
        REFERENCES public.hazard_assessments(id),

    severity TEXT NOT NULL CHECK (
        severity IN (
            'advisory',
            'watch',
            'warning'
        )
    ),

    title TEXT NOT NULL,
    message TEXT NOT NULL,

    status TEXT NOT NULL DEFAULT 'active'
        CHECK (
            status IN (
                'active',
                'resolved',
                'expired'
            )
        ),

    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,

    CHECK (
        expires_at IS NULL
        OR expires_at > issued_at
    ),

    CHECK (
        resolved_at IS NULL
        OR resolved_at >= issued_at
    ),

    UNIQUE (assessment_id, severity)
);


-- 6. PERFORMANCE INDEXES

CREATE INDEX IF NOT EXISTS idx_weather_daily_date
ON public.weather_daily (observation_date);

CREATE INDEX IF NOT EXISTS idx_forecast_commune_time
ON public.weather_forecasts (
    commune_code,
    valid_at,
    retrieved_at DESC
);

CREATE INDEX IF NOT EXISTS idx_fire_geom
ON public.fire_detections USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_fire_date
ON public.fire_detections (detected_at);

CREATE INDEX IF NOT EXISTS idx_fire_commune
ON public.fire_detections (commune_code);

CREATE INDEX IF NOT EXISTS idx_hazard_commune_type
ON public.hazard_assessments (
    commune_code,
    hazard_type,
    valid_from DESC
);

CREATE INDEX IF NOT EXISTS idx_alert_status
ON public.hazard_alerts (
    status,
    issued_at DESC
);

COMMIT;
