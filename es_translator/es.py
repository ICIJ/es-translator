class TranslatedHit():
    def __init__(self, hit, source_field = 'content', target_field = 'content_translated'):
        self.hit = hit
        self.source_field = source_field
        self.target_field = target_field
        # Ensure the target field is an array
        self.hit[self.target_field] = self.translations

    @property
    def source_value(self):
        return self.hit.to_dict().get(self.source_field)

    @property
    def translations(self):
        return self.hit.to_dict().get(self.target_field, [])

    @property
    def id(self):
        return self.hit.meta.id

    @property
    def routing(self):
        # Some documents don't have a routing property
        return self.hit.meta.to_dict().get('routing', None)

    @property
    def index(self):
        return self.hit.meta.index

    @property
    def doc_type(self):
        return self.hit.meta.doc_type

    @property
    def body(self):
        body = dict(doc=dict())
        body['doc'][self.target_field] = self.translations
        return body

    def save(self, client):
        client.update(index = self.index, doc_type = self.doc_type, id = self.id, routing = self.routing, body = self.body)

    def add_translation(self, apertium):
        if not self.is_translated(apertium.source_name, apertium.target_name):
            self.hit[self.target_field].append(dict(
                translator = 'APERTIUM',
                source_language = apertium.source_name.upper(),
                target_language = apertium.target_name.upper(),
                content = apertium.translate(self.source_value)))

    def is_translated(self, source_language, target_language):
        same_languages = lambda t: t['source_language'] == source_language.upper() and t['target_language'] == target_language.upper()
        return any(t for t in self.translations if same_languages(t))
