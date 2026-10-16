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

-- 1x1 transparent PNG
INSERT INTO book (id, isbn13, title, author, publisher, pdate, quantity, marc_tags, front_cover)
VALUES
 ('0345391802', '9780345391803', 'The Hitchhiker''s Guide to the Galaxy', 'Douglas Adams',
  'Del Rey', '1995', 2, 'SECRET-MARC',
  decode('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082', 'hex')),
 ('0441172717', '9780441172719', 'Dune', 'Frank Herbert', 'Ace', '1990', 1, NULL, NULL),
 ('0000000001', '9780000000019', '100% Wild_Cards', 'Test Author', 'Test Press', '2000', 1, NULL, NULL);

INSERT INTO item_borrower (item_oid, type, memberid) VALUES (1, 'Book', 'M1'), (2, 'Book', 'M2');
