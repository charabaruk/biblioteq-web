-- Minimal subset of the BiblioteQ SQLite schema, for integration tests only.
CREATE TABLE book (
  myoid INTEGER PRIMARY KEY AUTOINCREMENT,
  id TEXT, isbn13 TEXT, title TEXT NOT NULL, author TEXT, publisher TEXT,
  pdate TEXT, place TEXT, edition TEXT, category TEXT, language TEXT,
  quantity INTEGER NOT NULL DEFAULT 1, location TEXT, keyword TEXT, description TEXT,
  marc_tags TEXT, front_cover BLOB, back_cover BLOB
);
CREATE TABLE item_borrower (
  myoid INTEGER PRIMARY KEY AUTOINCREMENT, item_oid INTEGER NOT NULL, type TEXT NOT NULL,
  memberid TEXT, copyid TEXT, reserved_date TEXT, duedate TEXT
);
-- Test-only related table that exercises table sections.
CREATE TABLE book_note (
  myoid INTEGER PRIMARY KEY AUTOINCREMENT, item_oid INTEGER NOT NULL,
  grp INTEGER NOT NULL, seq INTEGER NOT NULL, note TEXT NOT NULL
);

-- Cover is a 1x1 transparent PNG.
INSERT INTO book (id, isbn13, title, author, publisher, pdate, quantity, marc_tags, front_cover)
VALUES
 ('0345391802', '9780345391803', 'The Hitchhiker''s Guide to the Galaxy', 'Douglas Adams',
  'Del Rey', '1995', 2, 'SECRET-MARC',
  X'89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082'),
 ('0441172717', '9780441172719', 'Dune', 'Frank Herbert', 'Ace', '1990', 1, NULL, NULL),
 ('0000000001', '9780000000019', '100% Wild_Cards', 'Test Author', 'Test Press', '2000', 1, NULL, NULL);

INSERT INTO item_borrower (item_oid, type, memberid) VALUES (1, 'Book', 'M1'), (2, 'Book', 'M2');

UPDATE book SET description = 'A comic <i>space</i> opera.' || char(10) || 'Second line.',
  keyword = 'comedy, towel'
WHERE isbn13 = '9780345391803';

-- Placeholder values that must be treated as empty; "N/A Station" is real content.
UPDATE book SET description = '  N/A  ', edition = 'N/A', place = 'N/A Station'
WHERE isbn13 = '9780000000019';

-- Inserted out of order on purpose.
INSERT INTO book_note (item_oid, grp, seq, note) VALUES
 (1, 2, 2, 'Four'), (1, 1, 2, 'Two'), (1, 2, 1, 'Three'), (1, 1, 1, 'One');
