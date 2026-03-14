-- Migration: 001_create_partysupport
-- Creates the LlmApp_partysupport table to store CSV survey data

CREATE TABLE IF NOT EXISTS "LlmApp_partysupport" (
    id          BIGSERIAL PRIMARY KEY,
    outcome     TEXT NOT NULL,
    group_variable TEXT NOT NULL,
    group_label TEXT NOT NULL,
    n           BIGINT,
    n_flag      TEXT,
    pct_lib     DOUBLE PRECISION,
    pct_con     DOUBLE PRECISION,
    pct_ndp     DOUBLE PRECISION,
    pct_bq      DOUBLE PRECISION,
    pct_grn     DOUBLE PRECISION,
    pct_other   DOUBLE PRECISION,
    pct_none    DOUBLE PRECISION,
    none_label  TEXT,
    year        BIGINT,
    dataset     TEXT,
    mode        TEXT,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
