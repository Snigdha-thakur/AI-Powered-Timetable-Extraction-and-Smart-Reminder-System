create table if not exists timetables (
    id          uuid primary key default gen_random_uuid(),
    user_id     text not null,
    data        jsonb not null,
    raw_data    jsonb not null,
    created_at  timestamptz default now()
);

create table if not exists reminders (
    id            uuid primary key default gen_random_uuid(),
    timetable_id  uuid references timetables(id) on delete cascade,
    day           text not null,
    time          text not null,
    subject       text not null,
    faculty       text not null default '',
    created_at    timestamptz default now()
);
