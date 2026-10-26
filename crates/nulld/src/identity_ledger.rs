//! Bounded native identity ledger for framework keys, not a database engine.
//! Exact identity is separate from approximate HRSA/AMN recall.
//! The ledger can be serialized into the daemon's existing postcard snapshots.

use serde::{Deserialize, Serialize};

const MAX_RECORDS: usize = 4096;
const MAX_VALUE_BYTES: usize = 64 * 1024;

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct MemoryRecord {
    pub namespace: Vec<String>,
    pub key: String,
    pub value: serde_json::Value,
    pub revision: u64,
}

#[derive(Default, Debug, Serialize, Deserialize)]
pub struct IdentityLedger {
    revision: u64,
    records: Vec<MemoryRecord>,
}

#[derive(Debug, PartialEq)]
pub enum LedgerError {
    InvalidIdentity,
    InvalidValue,
    CapacityExceeded,
}

impl IdentityLedger {
    fn validate(namespace: &[String], key: &str) -> Result<(), LedgerError> {
        if namespace.is_empty()
            || namespace.len() > 32
            || namespace.iter().any(|part| part.is_empty() || part.len() > 256)
            || key.is_empty()
            || key.len() > 256
        {
            return Err(LedgerError::InvalidIdentity);
        }
        Ok(())
    }

    pub fn put(
        &mut self,
        namespace: &[String],
        key: &str,
        value: serde_json::Value,
    ) -> Result<u64, LedgerError> {
        Self::validate(namespace, key)?;
        if !value.is_object()
            || serde_json::to_vec(&value)
                .map_err(|_| LedgerError::InvalidValue)?
                .len()
                > MAX_VALUE_BYTES
        {
            return Err(LedgerError::InvalidValue);
        }
        let position = self
            .records
            .iter()
            .position(|r| r.namespace == namespace && r.key == key);
        if position.is_none() && self.records.len() >= MAX_RECORDS {
            return Err(LedgerError::CapacityExceeded);
        }
        self.revision = self.revision.checked_add(1).ok_or(LedgerError::CapacityExceeded)?;
        let record = MemoryRecord {
            namespace: namespace.to_vec(),
            key: key.to_owned(),
            value,
            revision: self.revision,
        };
        if let Some(index) = position {
            self.records[index] = record;
        } else {
            self.records.push(record);
        }
        Ok(self.revision)
    }

    pub fn get(&self, namespace: &[String], key: &str) -> Option<&MemoryRecord> {
        self.records
            .iter()
            .find(|r| r.namespace == namespace && r.key == key)
    }

    pub fn delete(&mut self, namespace: &[String], key: &str) -> Result<bool, LedgerError> {
        Self::validate(namespace, key)?;
        if let Some(index) = self
            .records
            .iter()
            .position(|r| r.namespace == namespace && r.key == key)
        {
            self.revision = self.revision.checked_add(1).ok_or(LedgerError::CapacityExceeded)?;
            self.records.remove(index);
            return Ok(true);
        }
        Ok(false)
    }

    pub fn search(&self, prefix: &[String], offset: usize, limit: usize) -> Vec<MemoryRecord> {
        let mut found: Vec<_> = self
            .records
            .iter()
            .filter(|r| r.namespace.starts_with(prefix))
            .cloned()
            .collect();
        found.sort_by(|a, b| (&a.namespace, &a.key).cmp(&(&b.namespace, &b.key)));
        found.into_iter().skip(offset).take(limit.min(MAX_RECORDS)).collect()
    }

    pub fn namespaces(&self, prefix: &[String]) -> Vec<Vec<String>> {
        let mut found: Vec<_> = self
            .records
            .iter()
            .filter(|r| r.namespace.starts_with(prefix))
            .map(|r| r.namespace.clone())
            .collect();
        found.sort();
        found.dedup();
        found
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exact_multi_key_crud_and_prefix_pagination() {
        let mut ledger = IdentityLedger::default();
        let a = vec!["tenant".into(), "agent".into()];
        let b = vec!["tenant".into(), "other".into()];
        ledger.put(&a, "first", serde_json::json!({"v": 1})).unwrap();
        ledger.put(&a, "second", serde_json::json!({"v": 2})).unwrap();
        ledger.put(&b, "first", serde_json::json!({"v": 3})).unwrap();
        ledger.put(&a, "first", serde_json::json!({"v": 4})).unwrap();
        assert_eq!(ledger.get(&a, "first").unwrap().value["v"], 4);
        assert_eq!(ledger.search(&["tenant".into()], 1, 1).len(), 1);
        assert_eq!(ledger.namespaces(&["tenant".into()]).len(), 2);
        assert!(ledger.delete(&a, "first").unwrap());
        assert!(ledger.get(&a, "first").is_none());
        assert_eq!(ledger.get(&a, "second").unwrap().value["v"], 2);
    }

    #[test]
    fn postcard_roundtrip_preserves_identity() {
        let mut ledger = IdentityLedger::default();
        let namespace = vec!["team".into()];
        ledger.put(&namespace, "key", serde_json::json!({"text": "hello"})).unwrap();
        let bytes = postcard::to_stdvec(&ledger).unwrap();
        let restored: IdentityLedger = postcard::from_bytes(&bytes).unwrap();
        assert_eq!(restored.get(&namespace, "key").unwrap().value["text"], "hello");
    }

    #[test]
    fn rejects_invalid_and_oversized_payloads() {
        let mut ledger = IdentityLedger::default();
        assert_eq!(ledger.put(&[], "x", serde_json::json!({})), Err(LedgerError::InvalidIdentity));
        assert_eq!(
            ledger.put(&["team".into()], "x", serde_json::json!([1, 2])),
            Err(LedgerError::InvalidValue)
        );
    }
}
