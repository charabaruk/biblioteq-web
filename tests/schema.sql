-- Minimal subset of the BiblioteQ PostgreSQL schema, for integration tests only.
CREATE TABLE book (
  myoid bigserial PRIMARY KEY,
  id text, isbn13 text, title text NOT NULL, author text, publisher text,
  pdate text, place text, edition text, category text, language text,
  quantity integer NOT NULL DEFAULT 1, location text, keyword text, description text,
  marc_tags text, front_cover bytea, back_cover bytea
);
CREATE TABLE item_borrower (
  myoid bigserial PRIMARY KEY, item_oid bigint NOT NULL, type text NOT NULL,
  memberid text, copyid text, reserved_date text, duedate text
);
CREATE TABLE journal (
  myoid bigint PRIMARY KEY, title text NOT NULL,
  display_number integer, issueno integer NOT NULL DEFAULT 0,
  issuevolume integer NOT NULL DEFAULT 0
);
CREATE TABLE magazine (
  myoid bigint PRIMARY KEY, title text NOT NULL,
  display_number integer, issueno integer NOT NULL DEFAULT 0,
  issuevolume integer NOT NULL DEFAULT 0
);
CREATE TABLE book_copy_info (
  condition text, copy_number integer NOT NULL DEFAULT 1, copyid varchar(64) NOT NULL,
  item_oid bigint NOT NULL, myoid bigserial UNIQUE, notes text, originality text,
  status text, PRIMARY KEY (copyid, item_oid)
);
CREATE TABLE cd_copy_info (
  copy_number integer NOT NULL DEFAULT 1, copyid varchar(64) NOT NULL,
  item_oid bigint NOT NULL, myoid bigserial UNIQUE, notes text, status text,
  PRIMARY KEY (copyid, item_oid)
);
CREATE TABLE dvd_copy_info (
  copy_number integer NOT NULL DEFAULT 1, copyid varchar(64) NOT NULL,
  item_oid bigint NOT NULL, myoid bigserial UNIQUE, notes text, status text,
  PRIMARY KEY (copyid, item_oid)
);
CREATE TABLE journal_copy_info (
  copy_number integer NOT NULL DEFAULT 1, copyid varchar(64) NOT NULL,
  item_oid bigint NOT NULL, myoid bigserial UNIQUE, notes text, status text,
  PRIMARY KEY (copyid, item_oid)
);
CREATE TABLE magazine_copy_info (
  copy_number integer NOT NULL DEFAULT 1, copyid varchar(64) NOT NULL,
  item_oid bigint NOT NULL, myoid bigserial UNIQUE, notes text, status text,
  PRIMARY KEY (copyid, item_oid)
);
CREATE TABLE videogame_copy_info (
  copy_number integer NOT NULL DEFAULT 1, copyid varchar(64) NOT NULL,
  item_oid bigint NOT NULL, myoid bigserial UNIQUE, notes text, status text,
  PRIMARY KEY (copyid, item_oid)
);
-- Test-only related table that exercises table sections.
CREATE TABLE book_note (
  myoid bigserial PRIMARY KEY, item_oid bigint NOT NULL,
  grp integer NOT NULL, seq integer NOT NULL, note text NOT NULL
);

-- 1x1 transparent PNG
INSERT INTO book (id, isbn13, title, author, publisher, pdate, quantity, marc_tags, front_cover)
VALUES
 ('0345391802', '9780345391803', 'The Hitchhiker''s Guide to the Galaxy', 'Douglas Adams',
  'Del Rey', '1995', 2, 'SECRET-MARC',
  decode('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082', 'hex')),
 ('0441172717', '9780441172719', 'Dune', 'Frank Herbert', 'Ace', '1990', 1, NULL, NULL),
 ('0000000001', '9780000000019', '100% Wild_Cards', 'Test Author', 'Test Press', '2000', 1, NULL, NULL);

INSERT INTO item_borrower (item_oid, type, memberid) VALUES (1, 'Book', 'M1'), (2, 'Book', 'M2');
INSERT INTO journal (myoid, title, display_number, issueno, issuevolume) VALUES
 (1, 'Hidden Journal Values', -1, 0, 0),
 (2, 'Visible Journal Values', 42, 3, 2025);
INSERT INTO magazine (myoid, title, display_number, issueno, issuevolume) VALUES
 (1, 'Hidden Magazine Values', -1, 0, 0),
 (2, 'Visible Magazine Values', 42, 3, 2025);
INSERT INTO book_copy_info (item_oid, copyid, status, condition, originality, notes)
VALUES (1, 'barcode-1', 'UNKNOWN', ' UNKNOWN ', 'UNKNOWN', 'UNKNOWN');

UPDATE book SET description = E'A comic <i>space</i> opera.\nSecond line.',
  keyword = 'comedy, towel'
WHERE isbn13 = '9780345391803';

-- Placeholder values that must be treated as empty; "N/A Station" is real content.
UPDATE book SET description = '  N/A  ', edition = 'N/A', place = 'N/A Station'
WHERE isbn13 = '9780000000019';

-- Inserted out of order on purpose.
INSERT INTO book_note (item_oid, grp, seq, note) VALUES
 (1, 2, 2, 'Four'), (1, 1, 2, 'Two'), (1, 2, 1, 'Three'), (1, 1, 1, 'One');
