-- One row per member and month once a reconciliation has asked the partner about them. A row is
-- either reconciled, with the bonus the partner granted, or pending, with none.
CREATE TABLE reconciliations (
    member       text NOT NULL,
    month        text NOT NULL,
    status       text NOT NULL CHECK (status IN ('reconciled', 'pending')),
    bonus_points integer CHECK (bonus_points >= 0),
    PRIMARY KEY (member, month),
    CHECK ((status = 'reconciled') = (bonus_points IS NOT NULL))
);
